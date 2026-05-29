"""Routes for chatbot APIs."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from controllers.chat_controller import chat_controller, chat_history_controller
from model.chat_model import ChatRequest
from services.auth_service import get_current_user_optional


logger = logging.getLogger(__name__)

chat_router = APIRouter(tags=["chat"])


@chat_router.post("/message")
def chat_message(
	request: ChatRequest,
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Handle chat messages for the health assistant."""
	logger.info("POST /chat/message called")
	return chat_controller(request, current_user)


@chat_router.get("/history")
def chat_history(
	conversation_id: Optional[str] = None,
	config_id: Optional[str] = None,
	limit: int = Query(50, ge=1, le=200),
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Fetch chat history for the current user."""
	user_id = current_user.get("id") if current_user else None
	logger.info("GET /chat/history called")
	return chat_history_controller(user_id, conversation_id, config_id, limit)
