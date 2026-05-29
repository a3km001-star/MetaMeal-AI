"""Pydantic request/response models for chatbot endpoints."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


ChatRole = Literal["user", "assistant", "tool"]


class ChatMessage(BaseModel):
	role: ChatRole
	content: str
	created_at: Optional[datetime] = None


class ChatRequest(BaseModel):
	"""Validated input payload for chat requests."""

	message: str = Field(..., min_length=1)
	user_id: Optional[str] = None
	conversation_id: Optional[str] = None
	config_id: Optional[str] = None


class ChatResponse(BaseModel):
	"""Structured chat response returned to the client."""

	reply: str
	tool_calls: List[str] = Field(default_factory=list)


class ChatHistoryResponse(BaseModel):
	"""Structured chat history returned to the client."""

	messages: List[ChatMessage] = Field(default_factory=list)