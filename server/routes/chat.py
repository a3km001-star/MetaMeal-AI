"""Routes for chatbot APIs."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends

from controllers.chat_controller import chat_controller
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
