from typing import Any, Literal

from pydantic import BaseModel, Field


IntentType = Literal[
    "get_ticket",
    "add_comment",
    "assign_ticket",
    "get_order",
    "refund_check",
    "fallback",
]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str = "demo-user"


class ChatResponse(BaseModel):
    intent: IntentType
    answer: str
    tool_calls: list[dict[str, Any]]


class RefundCheckPayload(BaseModel):
    reason: str
