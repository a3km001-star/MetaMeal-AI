"""Controller functions for workout planner API endpoints."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException
from pydantic import ValidationError

from model.workout_model import WorkoutRequest
from db.mongo import workout_plans_collection
from services.workout_engine.planner import create_workout_plan_response


logger = logging.getLogger(__name__)


def generate_workout_plan_controller(
	request_data: Union[WorkoutRequest, Dict[str, Any]],
	current_user: Optional[dict] = None,
) -> Dict[str, Any]:
	"""Validate request and return deterministic weekly workout plan."""
	try:
		payload = request_data if isinstance(request_data, WorkoutRequest) else WorkoutRequest(**request_data)
		response = create_workout_plan_response(payload)
		try:
			user_id = payload.user_id or (current_user.get("id") if current_user else None)
			workout_plans_collection.insert_one(
				{
					"user_id": user_id,
					"created_at": datetime.now(timezone.utc),
					"plan": response,
				}
			)
		except Exception as exc:
			logger.warning("Failed to persist workout plan for chat tools: %s", exc)
		return {
			"success": True,
			"message": "Workout plan generated successfully",
			"data": response,
		}
	except ValidationError as exc:
		logger.warning("Invalid workout generation input: %s", exc)
		raise HTTPException(status_code=400, detail={"message": "Invalid input data", "errors": exc.errors()})
	except HTTPException:
		raise
	except Exception:
		logger.exception("Workout generation failed with internal error")
		raise HTTPException(status_code=500, detail="Internal server error while generating workout plan")


def get_latest_workout_plan_controller(current_user: Optional[dict] = None) -> Dict[str, Any]:
	"""Retrieve the latest workout plan for the current user."""
	try:
		if not current_user or not current_user.get("id"):
			raise HTTPException(status_code=401, detail="Unauthorized")

		user_id = current_user.get("id")
		latest_plan = workout_plans_collection.find_one(
			{"user_id": user_id},
			sort=[("created_at", -1)]
		)

		if not latest_plan:
			return {
				"success": True,
				"message": "No workout plan found",
				"data": None,
			}

		return {
			"success": True,
			"message": "Workout plan retrieved successfully",
			"data": {
				"plan": latest_plan.get("plan"),
				"created_at": latest_plan.get("created_at"),
			},
		}
	except HTTPException:
		raise
	except Exception as exc:
		logger.exception("Failed to retrieve workout plan: %s", exc)
		raise HTTPException(status_code=500, detail="Failed to retrieve workout plan")
