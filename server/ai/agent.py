"""Groq-powered chat agent with tool calling."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from ai.prompts import SYSTEM_PROMPT
from ai.tools import TOOL_FUNCTIONS, format_tool_output, get_tool_definitions
from db.mongo import chat_history_collection
from services.workout_engine.llm_generator import (
	DEFAULT_GROQ_MODEL,
	FALLBACK_GROQ_MODEL,
	GROQ_BASE_URL,
)


logger = logging.getLogger(__name__)

SERVER_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(SERVER_ROOT / ".env")


class ChatAgentError(RuntimeError):
	"""Raised when the chatbot fails to produce a response."""


def _load_history(
	user_id: str,
	conversation_id: Optional[str],
	config_id: Optional[str],
	limit: int = 8,
) -> List[Dict[str, str]]:
	query: Dict[str, Any] = {"user_id": user_id}
	if conversation_id:
		query["conversation_id"] = conversation_id
	if config_id:
		query["config_id"] = config_id

	items = list(
		chat_history_collection.find(query)
		.sort("created_at", -1)
		.limit(limit)
	)
	items.reverse()
	return [{"role": item.get("role", "user"), "content": item.get("content", "")} for item in items]


def get_history(
	user_id: str,
	conversation_id: Optional[str],
	config_id: Optional[str],
	limit: int = 50,
) -> List[Dict[str, Any]]:
	query: Dict[str, Any] = {"user_id": user_id}
	if conversation_id:
		query["conversation_id"] = conversation_id
	if config_id:
		query["config_id"] = config_id

	items = list(
		chat_history_collection.find(query)
		.sort("created_at", -1)
		.limit(limit)
	)
	items.reverse()
	return [
		{
			"role": item.get("role", "user"),
			"content": item.get("content", ""),
			"created_at": item.get("created_at"),
		}
		for item in items
	]


def _save_message(
	user_id: str,
	role: str,
	content: str,
	conversation_id: Optional[str],
	config_id: Optional[str],
) -> None:
	chat_history_collection.insert_one(
		{
			"user_id": user_id,
			"conversation_id": conversation_id,
			"config_id": config_id,
			"role": role,
			"content": content,
			"created_at": datetime.now(timezone.utc),
		}
	)



def _call_groq(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
	api_key = os.getenv("GROQ_API_KEY", "").strip()
	if not api_key:
		raise ChatAgentError("GROQ_API_KEY is not configured")

	models_to_try = [
		DEFAULT_GROQ_MODEL,
		os.getenv("GROQ_FALLBACK_MODEL", FALLBACK_GROQ_MODEL).strip() or FALLBACK_GROQ_MODEL,
	]
	last_error = ""

	for model in models_to_try:
		payload = {
			"model": model,
			"temperature": 0.2,
			"max_tokens": 800,
			"messages": messages,
		}
		if tools is not None:
			payload["tools"] = tools
			payload["tool_choice"] = "auto"

		try:
			response = requests.post(
				GROQ_BASE_URL,
				headers={
					"Authorization": f"Bearer {api_key}",
					"Content-Type": "application/json",
				},
				json=payload,
				timeout=30,
			)
		except requests.RequestException as exc:
			raise ChatAgentError(f"Groq network error: {exc}")

		try:
			response_data = response.json()
		except ValueError as exc:
			raise ChatAgentError(f"Groq returned non-JSON response: {exc}")

		if response.status_code >= 400:
			message = response_data.get("error", {}).get("message", "unknown error")
			error_code = str(response_data.get("error", {}).get("code", "")).lower()
			last_error = f"Groq API error {response.status_code}: {message}"
			is_decommissioned = (
				response.status_code == 400
				and ("decommissioned" in error_code or "decommissioned" in message.lower())
			)
			if is_decommissioned:
				continue
			raise ChatAgentError(last_error)

		return response_data

	raise ChatAgentError(last_error or "Groq API error")


def _call_groq_without_tools(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
	return _call_groq(messages, tools=None)


def _extract_tool_calls(message: Dict[str, Any]) -> List[Dict[str, Any]]:
	return message.get("tool_calls", []) if isinstance(message, dict) else []


def _execute_tool_call(tool_call: Dict[str, Any], user_id: str) -> Tuple[str, str]:
	function_data = tool_call.get("function", {})
	name = function_data.get("name")
	arguments = function_data.get("arguments", "{}")
	try:
		parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
	except json.JSONDecodeError:
		parsed_args = {}

	if parsed_args.get("user_id") in {None, "", "current_user"}:
		parsed_args["user_id"] = user_id

	logger.info("Tool call requested: %s args=%s", name, parsed_args)

	tool_fn = TOOL_FUNCTIONS.get(name)
	if not tool_fn:
		return name or "unknown", format_tool_output({"available": False, "message": "Tool not implemented"})

	try:
		result = tool_fn(**parsed_args)
		logger.info("Tool call result: %s available=%s", name, result.get("available"))
	except Exception as exc:
		logger.warning("Tool %s failed: %s", name, exc)
		result = {"available": False, "message": f"Tool error: {exc}"}

	return name, format_tool_output(result)


def run_chat(
	message: str,
	user_id: str,
	conversation_id: Optional[str] = None,
	config_id: Optional[str] = None,
) -> Tuple[str, List[str]]:
	"""Run the chat agent and return the final response plus tool call names."""
	messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
	messages.extend(_load_history(user_id, conversation_id, config_id))
	messages.append({"role": "user", "content": message})

	tool_definitions = get_tool_definitions()
	tool_call_names: List[str] = []

	response_data = _call_groq(messages, tool_definitions)
	choices = response_data.get("choices", [])
	if not choices:
		raise ChatAgentError("Groq returned no choices")

	assistant_message = choices[0].get("message", {})
	tool_calls = _extract_tool_calls(assistant_message)

	if tool_calls:
		messages.append({"role": "assistant", "content": assistant_message.get("content", ""), "tool_calls": tool_calls})
		for call in tool_calls:
			call_id = call.get("id")
			name, content = _execute_tool_call(call, user_id)
			tool_call_names.append(name)
			tool_message = {"role": "tool", "tool_call_id": call_id, "content": content}
			messages.append(tool_message)

		response_data = _call_groq(messages, tool_definitions)
		choices = response_data.get("choices", [])
		if not choices:
			raise ChatAgentError("Groq returned no choices after tool calls")
		assistant_message = choices[0].get("message", {})

	final_text = assistant_message.get("content", "").strip()
	if not final_text and tool_calls:
		logger.warning("Assistant returned empty content; retrying without tools")
		messages.append(
			{
				"role": "user",
				"content": "Summarize the tool outputs for the user in a concise response.",
			}
		)
		response_data = _call_groq_without_tools(messages)
		choices = response_data.get("choices", [])
		assistant_message = choices[0].get("message", {}) if choices else {}
		final_text = assistant_message.get("content", "").strip()

	if not final_text:
		logger.warning("Assistant returned empty content; sending fallback response")
		final_text = "I could not generate a response right now. Please try again or ask another question."

	_save_message(user_id, "user", message, conversation_id, config_id)
	_save_message(user_id, "assistant", final_text, conversation_id, config_id)

	return final_text, tool_call_names