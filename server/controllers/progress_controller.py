"""Controller functions for progress endpoints."""

from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException

from db.mongo import progress_logs_collection
from model.progress_model import ProgressLogRequest
from services.analytics_service import build_progress_summary


def _resolve_user_id(request: ProgressLogRequest, current_user: Optional[dict]) -> str:
	user_id = request.user_id or (current_user.get("id") if current_user else None)
	if not user_id:
		raise HTTPException(status_code=400, detail="user_id is required")
	return user_id


def log_progress_controller(request: ProgressLogRequest, current_user: Optional[dict] = None) -> Dict[str, Any]:
	"""Save a daily progress log entry."""
	user_id = _resolve_user_id(request, current_user)
	log_date = request.date or date.today().isoformat()

	payload: Dict[str, Any] = {
		"user_id": user_id,
		"date": log_date,
		"weight": request.weight,
		"consumed_calories": request.consumed_calories,
		"notes": request.notes,
		"updated_at": datetime.now(timezone.utc),
	}

	progress_logs_collection.update_one(
		{"user_id": user_id, "date": log_date},
		{"$set": payload, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
		upsert=True,
	)

	return {
		"success": True,
		"message": "Progress logged",
		"data": payload,
	}


def get_progress_controller(user_id: str) -> Dict[str, Any]:
	if not user_id:
		raise HTTPException(status_code=400, detail="user_id is required")

	logs = list(
		progress_logs_collection.find({"user_id": user_id})
		.sort("date", -1)
		.limit(14)
	)

	weights = [log.get("weight") for log in logs if isinstance(log.get("weight"), (int, float))]
	summary = build_progress_summary(weights)

	return {
		"success": True,
		"message": "Progress history fetched",
		"data": {
			"summary": summary,
			"logs": logs,
		},
	}