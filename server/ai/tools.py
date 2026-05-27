"""Tool definitions and implementations for the chatbot."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from db.mongo import (
	meal_plans_collection,
	progress_logs_collection,
	users_collection,
	workout_plans_collection,
)


def _safe_object_id(user_id: str) -> Optional[ObjectId]:
	try:
		return ObjectId(user_id)
	except Exception:
		return None


def _sanitize_value(value: Any) -> Any:
	if isinstance(value, dict):
		return {key: _sanitize_value(val) for key, val in value.items() if key != "_id"}
	if isinstance(value, list):
		return [_sanitize_value(item) for item in value]
	if isinstance(value, datetime):
		return value.isoformat()
	return value


def _sanitize_doc(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
	if not doc:
		return {}
	return _sanitize_value(doc)


def get_tool_definitions() -> List[Dict[str, Any]]:
	return [
		{
			"type": "function",
			"function": {
				"name": "meal_lookup_tool",
				"description": "Return the user's most recent meal plan.",
				"parameters": {
					"type": "object",
					"properties": {
						"user_id": {"type": "string"},
					},
					"required": ["user_id"],
				},
			},
		},
		{
			"type": "function",
			"function": {
				"name": "workout_lookup_tool",
				"description": "Return the user's most recent workout plan.",
				"parameters": {
					"type": "object",
					"properties": {
						"user_id": {"type": "string"},
					},
					"required": ["user_id"],
				},
			},
		},
		{
			"type": "function",
			"function": {
				"name": "progress_analysis_tool",
				"description": "Return progress insights for the last 7 days.",
				"parameters": {
					"type": "object",
					"properties": {
						"user_id": {"type": "string"},
						"range_days": {"type": "integer", "default": 7},
					},
					"required": ["user_id"],
				},
			},
		},
		{
			"type": "function",
			"function": {
				"name": "remaining_calories_tool",
				"description": "Return remaining calories for today based on logs and the latest meal plan.",
				"parameters": {
					"type": "object",
					"properties": {
						"user_id": {"type": "string"},
					},
					"required": ["user_id"],
				},
			},
		},
		{
			"type": "function",
			"function": {
				"name": "profile_lookup_tool",
				"description": "Return the user's profile details used for plans.",
				"parameters": {
					"type": "object",
					"properties": {
						"user_id": {"type": "string"},
					},
					"required": ["user_id"],
				},
			},
		},
	]


def meal_lookup_tool(user_id: str) -> Dict[str, Any]:
	if not user_id:
		return {"available": False, "message": "user_id is required"}

	plan = meal_plans_collection.find_one(
		{"user_id": user_id},
		sort=[("created_at", -1)],
	)
	if not plan:
		return {"available": False, "message": "No meal plan found for this user."}

	return {
		"available": True,
		"meal_plan": _sanitize_doc(plan.get("plan", {})),
		"created_at": _sanitize_value(plan.get("created_at")),
	}


def workout_lookup_tool(user_id: str) -> Dict[str, Any]:
	if not user_id:
		return {"available": False, "message": "user_id is required"}

	plan = workout_plans_collection.find_one(
		{"user_id": user_id},
		sort=[("created_at", -1)],
	)
	if not plan:
		return {"available": False, "message": "No workout plan found for this user."}

	return {
		"available": True,
		"workout_plan": _sanitize_doc(plan.get("plan", {})),
		"created_at": _sanitize_value(plan.get("created_at")),
	}


def profile_lookup_tool(user_id: str) -> Dict[str, Any]:
	object_id = _safe_object_id(user_id)
	if not object_id:
		return {"available": False, "message": "Invalid user_id"}

	user = users_collection.find_one({"_id": object_id})
	if not user:
		return {"available": False, "message": "User not found"}

	return {
		"available": True,
		"profile": user.get("user_details") or {},
		"name": user.get("name"),
	}


def progress_analysis_tool(user_id: str, range_days: int = 7) -> Dict[str, Any]:
	if not user_id:
		return {"available": False, "message": "user_id is required"}

	logs = list(
		progress_logs_collection.find({"user_id": user_id})
		.sort("date", -1)
		.limit(max(1, int(range_days)))
	)

	if not logs:
		return {"available": False, "message": "No progress logs found."}

	weights = [log.get("weight") for log in logs if isinstance(log.get("weight"), (int, float))]
	weight_delta = None
	if len(weights) >= 2:
		weight_delta = round(weights[0] - weights[-1], 2)

	return {
		"available": True,
		"summary": {
			"log_count": len(logs),
			"weight_change": weight_delta,
		},
		"logs": _sanitize_value(logs),
	}


def remaining_calories_tool(user_id: str) -> Dict[str, Any]:
	if not user_id:
		return {"available": False, "message": "user_id is required"}

	today = datetime.now(timezone.utc).date().isoformat()
	log = progress_logs_collection.find_one({"user_id": user_id, "date": today})
	latest_plan = meal_plans_collection.find_one({"user_id": user_id}, sort=[("created_at", -1)])

	if not log or not latest_plan:
		return {"available": False, "message": "Missing daily log or meal plan."}

	consumed = log.get("consumed_calories")
	calorie_target = None
	plan_payload = latest_plan.get("plan") or {}
	if isinstance(plan_payload, dict):
		calorie_target = plan_payload.get("calorie_target")

	if not isinstance(consumed, (int, float)) or not isinstance(calorie_target, (int, float)):
		return {"available": False, "message": "Calorie data unavailable."}

	remaining = round(calorie_target - consumed, 2)
	return {
		"available": True,
		"remaining_calories": remaining,
		"consumed_calories": consumed,
		"calorie_target": calorie_target,
	}


TOOL_FUNCTIONS = {
	"meal_lookup_tool": meal_lookup_tool,
	"workout_lookup_tool": workout_lookup_tool,
	"progress_analysis_tool": progress_analysis_tool,
	"remaining_calories_tool": remaining_calories_tool,
	"profile_lookup_tool": profile_lookup_tool,
}


def format_tool_output(payload: Dict[str, Any]) -> str:
	return json.dumps(payload, ensure_ascii=True)