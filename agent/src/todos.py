from langchain.agents import AgentState as BaseAgentState
from langchain.tools import ToolRuntime, tool
from langchain.messages import ToolMessage
from langgraph.types import Command
from typing import TypedDict, Literal
import uuid


class Todo(TypedDict):
    id: str
    title: str
    description: str
    emoji: str
    status: Literal["pending", "completed"]


class ChunkCitation(TypedDict):
    ref_id: int
    chunk_id: str
    doc_id: str
    doc_name: str
    content: str
    similarity: float
    dataset_id: str | None
    vector_similarity: float | None
    term_similarity: float | None


class DocAgg(TypedDict):
    doc_id: str
    doc_name: str
    count: int
    dataset_id: str | None


class MessageRAGContext(TypedDict):
    chunks: list[ChunkCitation]
    doc_aggs: list[DocAgg]


class AgentState(BaseAgentState):
    todos: list[Todo]
    # 按每轮用户提问的消息 ID 隔离存储切片与来源文档
    rag_citations: dict[str, MessageRAGContext]


@tool
def manage_todos(todos: list[Todo], runtime: ToolRuntime) -> Command:
    """
    Manage the current todos.
    """
    # Ensure all todos have IDs that are unique
    for todo in todos:
        if "id" not in todo or not todo["id"]:
            todo["id"] = str(uuid.uuid4())

    # Update the state
    return Command(
        update={
            "todos": todos,
            "messages": [
                ToolMessage(
                    content="Successfully updated todos",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


@tool
def get_todos(runtime: ToolRuntime):
    """
    Get the current todos.
    """
    return runtime.state.get("todos", [])


todo_tools = [
    manage_todos,
    get_todos,
]
