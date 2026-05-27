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