from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Department = Literal["auto", "hr", "devops", "finance", "pm", "developer"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    thread_id: Optional[str] = None
    department: Department = "auto"
    template_id: Optional[str] = None


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
    agent: str
    route_reason: Optional[str] = None
    artifacts: list[dict[str, Any]] = []
    parts: list[dict[str, Any]] = []  # multi-agent turns: [{"agent", "task", "ok"}]


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    agent: Optional[str] = None
    artifacts: list[dict[str, Any]] = []
    parts: list[dict[str, Any]] = []


class ThreadHistory(BaseModel):
    thread_id: str
    messages: list[HistoryMessage]


class TemplateInfo(BaseModel):
    template_id: str
    name: str
    description: str = ""
    placeholder_count: int
    uploaded_at: str
