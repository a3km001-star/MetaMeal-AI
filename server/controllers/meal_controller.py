"""Controller functions for meal planner API endpoints."""

import logging
from typing import Any, Dict, Union

from fastapi import HTTPException
from pydantic import ValidationError

from model.meal_model import MealRequest
from services.nutrition_engine.meal_planner import UserProfile, create_meal_plan_response


logger = logging.getLogger(__name__)


def generate_meal_plan_controller(request_data: Union[MealRequest, Dict[str, Any]]) -> Dict[str, Any]:
	"""Validate input and generate a meal plan response for the API layer."""
	try:
		payload = request_data if isinstance(request_data, MealRequest) else MealRequest(**request_data)
		logger.info("Meal generation request received")

		user_profile = UserProfile(**payload.model_dump())
		response = create_meal_plan_response(user_profile)

		logger.info("Meal planner executed")
		logger.info("Meal plan successfully generated")

		return {
			"success": True,
			"message": "Meal plan generated successfully",
			"data": response,
		}

	except ValidationError as exc:
		logger.warning("Invalid meal generation input: %s", exc)
		raise HTTPException(
			status_code=400,
			detail={
				"message": "Invalid input data",
				"errors": exc.errors(),
			},
		)
	except HTTPException as exc:
		detail_text = str(exc.detail).lower()
		if exc.status_code == 400:
			logger.warning("Meal generation failed due to invalid request or no feasible plan: %s", exc.detail)
		elif "dataset" in detail_text or "file" in detail_text or "not found" in detail_text:
			logger.error("Meal generation failed due to dataset error: %s", exc.detail)
		else:
			logger.error("Meal generation failed with HTTP error: %s", exc.detail)
		raise
	except FileNotFoundError:
		logger.exception("Meal generation failed: dataset file missing")
		raise HTTPException(status_code=500, detail="Dataset file is missing")
	except Exception:
		logger.exception("Meal generation failed with internal error")
		raise HTTPException(status_code=500, detail="Internal server error while generating meal plan")