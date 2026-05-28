"""Service layer for chatbot interactions."""

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException

from ai.agent import ChatAgentError, get_history, run_chat


logger = logging.getLogger(__name__)


def handle_chat(
	message: str,
	user_id: Optional[str],
	conversation_id: Optional[str],
	config_id: Optional[str],
) -> Dict[str, Any]:
	if not user_id:
		raise HTTPException(status_code=400, detail="user_id is required for chat")

	try:
		reply, tool_calls = run_chat(
			message=message,
			user_id=user_id,
			conversation_id=conversation_id,
			config_id=config_id,
		)
		return {"reply": reply, "tool_calls": tool_calls}
	except ChatAgentError as exc:
		logger.warning("Chat agent error: %s", exc)
		raise HTTPException(status_code=500, detail=str(exc))
	except Exception as exc:
		logger.exception("Chat service failed")
		raise HTTPException(status_code=500, detail=f"Chat service error: {exc}")


def fetch_chat_history(
	user_id: Optional[str],
	conversation_id: Optional[str],
	config_id: Optional[str],
	limit: int = 50,
) -> Dict[str, Any]:
	if not user_id:
		raise HTTPException(status_code=400, detail="user_id is required for chat history")

	try:
		messages = get_history(
			user_id=user_id,
			conversation_id=conversation_id,
			config_id=config_id,
			limit=limit,
		)
		return {"messages": messages}
	except Exception as exc:
		logger.exception("Chat history fetch failed")
		raise HTTPException(status_code=500, detail=f"Chat history error: {exc}")