import os
import time
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.agents.factory import AgentMiddleware

# Ensure .env is loaded
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from src.ragflow_tool import search_ragflow_api


def is_title_generation_query(query: str) -> bool:
    """判断是否为 CopilotKit 内部自动生成会话标题的 prompt"""
    return "Generate a short title" in query or "Generate a title" in query


def extract_original_user_topic(messages: List[Any]) -> str:
    """从会话历史中提取用户的第一句真实提问作为标题"""
    for msg in messages:
        c = ""
        if isinstance(msg, HumanMessage):
            c = str(msg.content)
        elif isinstance(msg, dict) and msg.get("role") in ["user", "human"]:
            c = str(msg.get("content", ""))
        if c and not is_title_generation_query(c):
            # 截取前 15 个字作为简洁标题
            clean = c.strip().replace("\n", " ")
            return clean[:16] + ("..." if len(clean) > 16 else "")
    return "新对话"


def build_system_context_prompt(context_text: str, doc_names: List[str] | None = None) -> str:
    """组装包含前置切片与引用规范的标准 SystemMessage"""
    doc_count = len(doc_names) if doc_names else 1
    evolution_hint = ""
    if doc_count >= 2:
        evolution_hint = f"""
4. [政策比对判定指令]：本次检索命中了多个文件（{", ".join(doc_names or [])}）。
   - 触发比对条件（必须同时满足）：仅当这些文档针对【同一具体业务事项】（如电价标准演进、营业规则修订、光伏准入变更），存在明确的【前后更替、新旧版本演进或机制改变】时，必须在回答的同时调用 `comparePolicies` 工具（例如《关于2004年度北京市居民生活用电价格调整情况的报告》与《关于2012年至今北京市居民阶梯电价政策执行情况的报告》正是典型的同一城市居民电价历史演进，必须触发 comparePolicies！）。
   - 严禁强行比对：如果文档只是同属于电力领域但属于【完全不同的政策层级或不同事项】（例如上位法《电力法》与具体的《获得电力意见》并不存在直接条款修订替代关系），属于正常的政策协同，【严禁生拉硬拽进行对比】，切勿调用 `comparePolicies`！
"""

    return f"""=== 知识库事实上下文 (Knowledge Base Context) ===
{context_text}

[重要引用指令]：
1. 请严格根据上述知识库切片中的事实信息回答用户问题。
2. 凡引用知识库事实的具体句子，请在句末规范标注 [REF:n]（例如 [REF:1]）。
3. 标题、总结和非知识库内容切勿打标。{evolution_hint}
"""


def get_latest_user_message_id_and_query(messages: List[Any]) -> tuple[str, str]:
    """提取最后一条用户提问的 ID 与文本内容"""
    for msg in reversed(messages):
        content = ""
        msg_id = ""
        if isinstance(msg, HumanMessage):
            content = str(msg.content)
            msg_id = getattr(msg, "id", "") or str(id(msg))
        elif isinstance(msg, dict) and msg.get("role") in ["user", "human"]:
            content = str(msg.get("content", ""))
            msg_id = str(msg.get("id", "")) or str(id(msg))
        if content:
            return msg_id, content
    return "", ""


def _inject_context(
    messages: List[Any],
    context_text: str,
    refs: List[Dict[str, Any]],
    doc_aggs: List[Dict[str, Any]],
    user_msg_id: str,
    existing_citations: Dict[str, Any] | None = None,
) -> dict:
    """将 RAGFlow 检索结果注入为 SystemMessage，并将结构化切片与聚合文档按 user_msg_id 存入 state.rag_citations"""
    doc_names = list({r.get("doc_name", "未知") for r in refs})
    print(f"✅ RAGFlow 检索成功! 命中切片: {len(refs)} 条 | 来源文档: {doc_names}")

    system_context = build_system_context_prompt(context_text, doc_names)

    # 检查是否已存在 RAG SystemMessage，有则复用 ID 覆盖更新（避免 messages 重复追加）
    existing_index = -1
    for i, msg in enumerate(messages):
        content = getattr(msg, "content", "")
        if isinstance(content, str) and content.startswith("=== 知识库事实上下文"):
            existing_index = i
            break

    if existing_index != -1:
        existing_id = getattr(messages[existing_index], "id", None)
        context_msg = SystemMessage(content=system_context, id=existing_id)
        updated_messages = list(messages)
        updated_messages[existing_index] = context_msg
        print(f"🔄 已覆盖更新历史 RAG SystemMessage (id={existing_id})")
    else:
        context_msg = SystemMessage(content=system_context, id="rag_knowledge_context")
        # 插入到最后一条用户消息之前
        updated_messages = [*messages[:-1], context_msg, messages[-1]]
        print(f"💉 已成功向 Prompt 注入 RAG 知识库上下文 (位于用户输入之前)")

    # 组装结构化切片与来源文档数据
    default_ds = os.getenv("RAGFLOW_DATASET_IDS", "d4d0e9c6a05c11f199bf45be651e52f0").split(",")[0].strip()
    entry = {
        "chunks": [
            {
                "ref_id": r.get("ref_id", 0),
                "chunk_id": r.get("chunk_id", ""),
                "doc_id": r.get("doc_id", ""),
                "doc_name": r.get("doc_name", ""),
                "content": r.get("content", ""),
                "similarity": r.get("similarity", 0.0),
                "dataset_id": r.get("dataset_id") or default_ds,
                "vector_similarity": r.get("vector_similarity"),
                "term_similarity": r.get("term_similarity"),
            }
            for r in refs
        ],
        "doc_aggs": [
            {
                "doc_id": d.get("doc_id", ""),
                "doc_name": d.get("doc_name", ""),
                "count": d.get("count", 1),
                "dataset_id": d.get("dataset_id") or default_ds,
            }
            for d in doc_aggs
        ],
    }

    citations_dict = dict(existing_citations or {})
    if user_msg_id:
        citations_dict[user_msg_id] = entry

    print(f"📦 已将第 [{user_msg_id}] 轮切片与来源文档存入 AgentState.rag_citations")
    print(f"========================================================================\n")
    return {
        "messages": updated_messages,
        "rag_citations": citations_dict,
    }


class RAGIntentMiddleware(AgentMiddleware):
    """
    RAGFlow 前置切片注入中间件。

    在 Agent 运行前 (abefore_agent) 直接调用 RAGFlow 检索：
    - 遇到生成标题请求直接不执行 RAG
    - 若检索到相关切片 → 将其组装为 SystemMessage 注入 Prompt，并将结构化切片与文件聚合按 user_msg_id 存入 state.rag_citations
    - 若无相关结果   → 保持原始消息，模型自行回答
    - 增加短期查询缓存，防止在一次对话运行/重试时重复触发多次检索
    """
    def __init__(self):
        super().__init__()
        self._last_query = ""
        self._last_time = 0
        self._last_result = None

    def _should_skip_cache(self, query: str) -> bool:
        now = time.time()
        if query == self._last_query and (now - self._last_time) < 15:
            return False
        return True

    def before_agent(self, state: Any, runtime: Any = None) -> dict[str, Any] | None:
        """同步版本（仅在纯同步上下文使用，ASGI 环境由 abefore_agent 接管）"""
        messages = state.get("messages", [])
        if not messages:
            return None
        user_msg_id, latest_query = get_latest_user_message_id_and_query(messages)
        if not latest_query:
            return None

        # 过滤生成标题的请求，不进行 RAG 检索
        if is_title_generation_query(latest_query):
            return None

        existing_citations = state.get("rag_citations", {})

        # 检查防抖缓存
        if not self._should_skip_cache(latest_query) and self._last_result is not None:
            print(f"⚡ [RAG Middleware] 命中查询缓存 (15s内相同提问): '{latest_query}'，跳过重复请求")
            context_text, refs, doc_aggs = self._last_result
            return _inject_context(messages, context_text, refs, doc_aggs, user_msg_id, existing_citations)

        print(f"\n==================== [RAG Middleware: before_agent] ====================")
        print(f"📥 收到最新提问: '{latest_query}' (msg_id: {user_msg_id})")

        t_start = time.time()
        context_text, refs, doc_aggs = search_ragflow_api(latest_query)
        t_cost = int((time.time() - t_start) * 1000)
        print(f"⏱️  RAGFlow 检索耗时: {t_cost}ms")

        self._last_query = latest_query
        self._last_time = time.time()
        self._last_result = (context_text, refs, doc_aggs) if refs else None

        if refs:
            return _inject_context(messages, context_text, refs, doc_aggs, user_msg_id, existing_citations)

        print(f"⚠️  RAGFlow 未检索到相关切片，保持原始消息输入")
        print(f"========================================================================\n")
        return None

    async def abefore_agent(self, state: Any, runtime: Any = None) -> dict[str, Any] | None:
        """
        异步版本（ASGI 环境实际调用）。
        使用 asyncio.to_thread 将同步阻塞的 RAGFlow HTTP 请求放入线程池，
        避免阻塞 async 事件循环。
        """
        messages = state.get("messages", [])
        if not messages:
            return None
        user_msg_id, latest_query = get_latest_user_message_id_and_query(messages)
        if not latest_query:
            return None

        # 过滤生成标题的请求，绝不进行 RAG 检索，秒级返回
        if is_title_generation_query(latest_query):
            print(f"⚡ [RAG Middleware] 收到标题生成请求，跳过 RAG 检索")
            return None

        existing_citations = state.get("rag_citations", {})

        # 检查防抖缓存，避免同一轮轮询或中间件多次执行发起重复 HTTP 请求
        if not self._should_skip_cache(latest_query) and self._last_result is not None:
            print(f"⚡ [RAG Middleware] 命中查询缓存 (15s内相同提问): '{latest_query}'，直接复用切片，不重复请求 RAGFlow")
            context_text, refs, doc_aggs = self._last_result
            return _inject_context(messages, context_text, refs, doc_aggs, user_msg_id, existing_citations)

        print(f"\n==================== [RAG Middleware: abefore_agent] ====================")
        print(f"📥 收到最新提问: '{latest_query}' (msg_id: {user_msg_id})")

        t_start = time.time()
        context_text, refs, doc_aggs = await asyncio.to_thread(search_ragflow_api, latest_query)
        t_cost = int((time.time() - t_start) * 1000)
        print(f"⏱️  RAGFlow 检索耗时: {t_cost}ms")

        self._last_query = latest_query
        self._last_time = time.time()
        self._last_result = (context_text, refs, doc_aggs) if refs else None

        if refs:
            return _inject_context(messages, context_text, refs, doc_aggs, user_msg_id, existing_citations)

        print(f"⚠️  RAGFlow 未检索到相关切片，保持原始消息输入")
        print(f"========================================================================\n")
        return None
