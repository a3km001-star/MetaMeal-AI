"""Controller functions for meal planner API endpoints."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException
from pydantic import ValidationError

from model.meal_model import MealRequest
from db.mongo import meal_plans_collection
from services.auth_service import update_user_details, record_meal_generation_event
from services.nutrition_engine.meal_planner import UserProfile, create_meal_plan_response
from services.nutrition_engine.metabolic_calculator import Sex, ActivityLevel, FitnessGoal


logger = logging.getLogger(__name__)


def generate_meal_plan_controller(
	request_data: Union[MealRequest, Dict[str, Any]],
	current_user: Optional[dict] = None,
) -> Dict[str, Any]:
	"""Validate input and generate a meal plan response for the API layer."""
	try:
		payload = request_data if isinstance(request_data, MealRequest) else MealRequest(**request_data)
		logger.info("Meal generation request received")

		# Convert string values to enum instances for UserProfile
		user_profile_data = payload.model_dump()
		user_profile_data["sex"] = Sex(payload.sex)
		user_profile_data["activity_level"] = ActivityLevel(payload.activity_level)
		user_profile_data["goal"] = FitnessGoal(payload.goal)

		user_profile = UserProfile(**user_profile_data)

		if current_user is not None:
			try:
				record_meal_generation_event(current_user["id"], payload.model_dump(mode="json"))
			except Exception as exc:
				logger.warning("Failed to record meal generation metadata: %s", exc)

		response = create_meal_plan_response(user_profile)

		if current_user is not None:
			try:
				meal_plans_collection.insert_one(
					{
						"user_id": current_user.get("id"),
						"created_at": datetime.now(timezone.utc),
						"plan": response,
					}
				)
			except Exception as exc:
				logger.warning("Failed to persist meal plan for chat tools: %s", exc)

		if current_user is not None:
			try:
				update_user_details(current_user["id"], {
					"age": int(payload.age),
					"sex": payload.sex,
					"height": float(payload.height),
					"weight": float(payload.weight),
					"diet_type": payload.diet_type,
					"activity_level": payload.activity_level,
					"goal": payload.goal,
					"allergies": payload.allergies,
				})
			except Exception as exc:
				logger.warning("Failed to update user details: %s", exc)

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