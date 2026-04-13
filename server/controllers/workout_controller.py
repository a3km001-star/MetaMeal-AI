"""Controller functions for workout planner API endpoints."""

import logging
from typing import Any, Dict, Union

from fastapi import HTTPException
from pydantic import ValidationError

from model.workout_model import WorkoutRequest
from services.workout_engine.planner import create_workout_plan_response


logger = logging.getLogger(__name__)


def generate_workout_plan_controller(request_data: Union[WorkoutRequest, Dict[str, Any]]) -> Dict[str, Any]:
	"""Validate request and return deterministic weekly workout plan."""
	try:
		payload = request_data if isinstance(request_data, WorkoutRequest) else WorkoutRequest(**request_data)
		response = create_workout_plan_response(payload)
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