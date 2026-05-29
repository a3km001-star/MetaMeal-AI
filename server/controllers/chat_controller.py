"""Controller functions for chat endpoints."""

from typing import Any, Dict, Optional

from fastapi import HTTPException

from model.chat_model import ChatRequest
from services.chat_service import fetch_chat_history, handle_chat


def chat_controller(request: ChatRequest, current_user: Optional[dict] = None) -> Dict[str, Any]:
	"""Validate request and return chat response."""
	user_id = request.user_id or (current_user.get("id") if current_user else None)
	if not user_id:
		raise HTTPException(status_code=400, detail="user_id is required when not authenticated")

	data = handle_chat(
		message=request.message,
		user_id=user_id,
		conversation_id=request.conversation_id,
		config_id=request.config_id,
	)
	return {
		"success": True,
		"message": "Chat response generated",
		"data": data,
	}


def chat_history_controller(
	user_id: Optional[str],
	conversation_id: Optional[str],
	config_id: Optional[str],
	limit: int,
) -> Dict[str, Any]:
	data = fetch_chat_history(
		user_id=user_id,
		conversation_id=conversation_id,
		config_id=config_id,
		limit=limit,
	)
	return {
		"success": True,
		"message": "Chat history fetched",
		"data": data,
	}