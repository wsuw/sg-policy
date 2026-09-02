import os
import re
import json
import urllib.request
import urllib.error
import threading
from pathlib import Path
from dotenv import load_dotenv
from contextvars import ContextVar
from typing import Optional, List, Dict, Any, Tuple
from langchain.tools import tool

# Ensure .env is loaded from project root or current dir
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# ContextVar for thread-safe/async-safe reference storage
_ctx_references: ContextVar[List[Dict[str, Any]]] = ContextVar(
    "current_references", default=[]
)
_thread_local = threading.local()
_global_references: List[Dict[str, Any]] = []


def get_current_references() -> List[Dict[str, Any]]:
    """Retrieve the current references list across asyncio/threads."""
    try:
        refs = _ctx_references.get()
        if refs:
            return refs
    except LookupError:
        pass

    if hasattr(_thread_local, "refs") and _thread_local.refs:
        return _thread_local.refs

    return _global_references


def set_current_references(refs: List[Dict[str, Any]]) -> None:
    """Set the current references list across asyncio/threads."""
    _ctx_references.set(refs)
    _thread_local.refs = refs
    global _global_references
    _global_references = refs


def reset_current_references() -> None:
    """Reset the current references list."""
    _ctx_references.set([])
    _thread_local.refs = []
    global _global_references
    _global_references = []


def clean_chunk_content(raw_text: str) -> str:
    """
    清洗切片内容：
    1. 去除形如 'None：/', 'None: /', 'None：', 'None: ' 等无意义占位符
    2. 清理多余的分号、破折号和空白字符
    3. 合并多余换行并规整段落
    """
    if not raw_text:
        return ""

    text = raw_text

    # 替换常见的无意义标记
    text = re.sub(r"None\s*[:：]\s*/\s*;?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"None\s*[:：]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"none\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r";\s*;", ";", text)

    # 规范化标点与换行
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        l = line.strip(" ;,\t")
        if l and l not in ["/", ";", "--"]:
            cleaned_lines.append(l)

    result = "\n".join(cleaned_lines)
    # 消除连续空行与多余空格
    result = re.sub(r"\n{2,}", "\n", result)
    result = re.sub(r"[ \t]{2,}", " ", result)
    return result.strip()


def search_ragflow_api(
    question: str,
    dataset_ids: Optional[List[str]] = None,
    page: int = 1,
    size: int = 4,
    highlight: bool = True,
    search_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    调用 RAGFlow 知识库检索 API，清洗数据并暂存元数据。
    返回: (格式化后的纯文本供LLM使用, 引用元数据列表)
    """
    api_url = os.getenv("RAGFLOW_API_URL", "http://localhost/api/v1/datasets/search")
    api_key = os.getenv("RAGFLOW_API_KEY", "")

    default_dataset_ids = [
        d.strip()
        for d in os.getenv(
            "RAGFLOW_DATASET_IDS", "d4d0e9c6a05c11f199bf45be651e52f0"
        ).split(",")
        if d.strip()
    ]
    default_search_id = os.getenv(
        "RAGFLOW_SEARCH_ID", "337428d8a05f11f199bf45be651e52f0"
    )

    payload = {
        "page": page,
        "size": size,
        "highlight": highlight,
        "question": question,
        "search_id": search_id or default_search_id,
        "tenant_id": tenant_id,
        "dataset_ids": dataset_ids or default_dataset_ids,
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    chunks_data: List[Dict[str, Any]] = []
    doc_aggs: List[Dict[str, Any]] = []

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_json = json.loads(resp.read().decode("utf-8"))
            if resp_json.get("code") == 0 and "data" in resp_json:
                chunks_data = resp_json["data"].get("chunks", [])
                doc_aggs = resp_json["data"].get("doc_aggs", [])
            else:
                print(
                    f"[RAGFlow] API returned code={resp_json.get('code')}: {resp_json.get('message', '')}"
                )
    except Exception as e:
        print(f"[RAGFlow] Request to {api_url} failed: {e}")
        chunks_data = []
        doc_aggs = []

    if not chunks_data:
        return "未检索到与该问题相关的知识库切片内容。", [], []

    formatted_texts: List[str] = []
    refs: List[Dict[str, Any]] = []
    unique_doc_names: List[str] = []

    # 优先从 RAGFlow 接口返回的 doc_aggs 获取文档来源
    for doc in doc_aggs:
        d_name = doc.get("doc_name")
        if d_name and d_name not in unique_doc_names:
            unique_doc_names.append(d_name)
        if not doc.get("dataset_id"):
            doc["dataset_id"] = os.getenv("RAGFLOW_DATASET_IDS", "d4d0e9c6a05c11f199bf45be651e52f0").split(",")[0].strip()

    for i, chunk in enumerate(chunks_data):
        ref_num = i + 1
        chunk_id = chunk.get("chunk_id", "")
        raw_content = (
            chunk.get("content_with_weight") or chunk.get("content_ltks") or ""
        )
        cleaned = clean_chunk_content(raw_content)

        doc_name = chunk.get("docnm_kwd") or chunk.get("doc_name") or "未知文档"
        if doc_name != "未知文档" and doc_name not in unique_doc_names:
            unique_doc_names.append(doc_name)

        doc_id = chunk.get("doc_id", "")
        similarity = float(chunk.get("similarity", 0.0))
        vector_similarity = (
            float(chunk.get("vector_similarity", 0.0))
            if chunk.get("vector_similarity") is not None
            else None
        )
        term_similarity = (
            float(chunk.get("term_similarity", 0.0))
            if chunk.get("term_similarity") is not None
            else None
        )
        positions = chunk.get("positions", [])
        kb_id = chunk.get("kb_id", "")

        ref_meta = {
            "ref_id": ref_num,
            "ref_tag": f"[REF:{ref_num}]",
            "doc_id": doc_id,
            "doc_name": doc_name,
            "chunk_id": chunk_id,
            "kb_id": kb_id,
            "similarity": round(similarity, 4),
            "vector_similarity": (
                round(vector_similarity, 4)
                if vector_similarity is not None
                else None
            ),
            "term_similarity": (
                round(term_similarity, 4)
                if term_similarity is not None
                else None
            ),
            "content": cleaned,
            "raw_content": raw_content,
            "positions": positions,
        }
        refs.append(ref_meta)

        # 格式化为 RAGFlow 标准树形节点输出给 LLM
        formatted_entry = (
            f"[REF:{ref_num}]\n"
            f"├── Title: {doc_name} (相似度: {similarity:.2f})\n"
            f"└── Content:\n{cleaned}"
        )
        formatted_texts.append(formatted_entry)

    # 仅从实际检索命中的 refs 切片中聚合来源文档，不使用全库倒排索引返回的粗粒度 doc_aggs
    matched_doc_aggs: List[Dict[str, Any]] = []
    seen_docs = set()
    default_ds = os.getenv("RAGFLOW_DATASET_IDS", "d4d0e9c6a05c11f199bf45be651e52f0").split(",")[0].strip()

    for r in refs:
        d_name = r.get("doc_name", "")
        d_id = r.get("doc_id", "")
        if d_name and d_name != "未知文档" and d_name not in seen_docs:
            seen_docs.add(d_name)
            # 尝试在 RAGFlow 原生 doc_aggs 中查找匹配的 dataset_id
            matched_dataset_id = default_ds
            for orig_doc in doc_aggs:
                if orig_doc.get("doc_name") == d_name and orig_doc.get("dataset_id"):
                    matched_dataset_id = orig_doc.get("dataset_id")
                    break

            matched_doc_aggs.append({
                "doc_id": d_id,
                "doc_name": d_name,
                "count": 1,
                "dataset_id": matched_dataset_id,
            })

    # 存入 ContextVar / ThreadLocal
    set_current_references(refs)

    # 纯切片内容输出给 LLM 作为上下文
    tool_output = "\n\n".join(formatted_texts)
    return tool_output, refs, matched_doc_aggs


@tool
def ragflow_search(question: str) -> str:
    """
    检索企业知识库与政策规划文档（如十五五规划、分时阶梯电价、业务需求、技术规范、项目管理等）。
    当回答需要事实依据或具体政策内容时，必须调用此工具。
    返回值包含带编号的 [REF:n] 切片文本及真实来源文档列表 [DOC:文件名]。
    """
    output_text, _ = search_ragflow_api(question=question)
    return output_text


@tool
def calculate(expression: str) -> str:
    """
    辅助计算工具。用于执行精确的数学计算（如百分比变化、加减乘除、投资金额汇总等）。
    输入必须是合法的数学表达式，例如: '460 + 36' 或 '(0.85 - 0.20) * 100'。
    """
    try:
        # 只允许安全的数学字符
        if not re.match(r"^[\d\.\s\+\-\*\/\(\)\%]+$", expression):
            return "错误: 表达式包含不支持的字符"
        # 安全计算
        result = eval(expression, {"__builtins__": None}, {})
        if isinstance(result, float):
            result = round(result, 6)
            if result.is_integer():
                result = int(result)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算失败: {str(e)}"
