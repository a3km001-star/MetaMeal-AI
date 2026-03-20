"""Meal formatter for frontend-facing meal plan responses.

This module converts raw meal objects produced by the constraint solver into a
clean, structured response shape for the frontend. Only fields required by the
UI are preserved.
"""

import logging
from typing import Any, Dict


logger = logging.getLogger(__name__)

REQUIRED_MEAL_KEYS = ("breakfast", "lunch", "dinner", "snack")
REQUIRED_MEAL_FIELDS = ("name", "calories", "ingredients", "instructions")


def _validate_meal_dict(meal: Dict[str, Any], meal_key: str) -> None:
	"""Validate a raw single-meal dictionary before formatting."""
	if not isinstance(meal, dict):
		raise TypeError(f"Meal '{meal_key}' must be a dictionary")

	missing_fields = [field for field in REQUIRED_MEAL_FIELDS if field not in meal]
	if missing_fields:
		missing = ", ".join(missing_fields)
		raise ValueError(f"Meal '{meal_key}' is missing required fields: {missing}")

	for field in ("name", "ingredients", "instructions"):
		value = meal.get(field)
		if not isinstance(value, str) or not value.strip():
			raise ValueError(f"Meal '{meal_key}' has invalid or empty '{field}'")

	calories = meal.get("calories")
	if not isinstance(calories, (int, float)):
		raise TypeError(f"Meal '{meal_key}' calories must be numeric")
	if calories < 0:
		raise ValueError(f"Meal '{meal_key}' calories must be non-negative")


def format_single_meal(meal: Dict[str, Any]) -> Dict[str, Any]:
	"""Format a single raw meal object for frontend consumption.

	Args:
		meal: Raw meal dictionary containing at least name, calories,
			ingredients, and instructions.

	Returns:
		A cleaned meal dictionary with only frontend-required fields.

	Raises:
		TypeError: If meal is not a dictionary or calories is not numeric.
		ValueError: If required fields are missing or empty.
	"""
	_validate_meal_dict(meal, "meal")

	formatted = {
		"name": meal["name"].strip(),
		"calories": round(float(meal["calories"]), 2),
		"ingredients": meal["ingredients"].strip(),
		"instructions": meal["instructions"].strip(),
	}

	# Preserve optional serving scale metadata when provided by the planner.
	if "serving_multiplier" in meal:
		formatted["serving_multiplier"] = round(float(meal.get("serving_multiplier", 1.0) or 1.0), 2)

	return formatted


def format_meal_plan(meal_plan: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
	"""Format a raw meal-plan dictionary into a frontend response shape.

	Expected input shape:
		{
			"breakfast": {...},
			"lunch": {...},
			"dinner": {...},
			"snack": {...}
		}

	Returns:
		A dictionary with the same meal slots and only frontend fields.

	Raises:
		TypeError: If the meal plan is not a dictionary.
		ValueError: If the meal plan is empty or required meal keys/fields are
			missing.
	"""
	logger.debug("Formatting meal plan...")

	if meal_plan is None:
		raise ValueError("Meal plan cannot be None")
	if not isinstance(meal_plan, dict):
		raise TypeError("Meal plan must be a dictionary")
	if not meal_plan:
		raise ValueError("Meal plan cannot be empty")

	missing_meals = [meal_key for meal_key in REQUIRED_MEAL_KEYS if meal_key not in meal_plan]
	if missing_meals:
		missing = ", ".join(missing_meals)
		raise ValueError(f"Meal plan is missing required meals: {missing}")

	formatted_plan: Dict[str, Dict[str, Any]] = {}
	for meal_key in REQUIRED_MEAL_KEYS:
		raw_meal = meal_plan.get(meal_key)
		if raw_meal is None:
			raise ValueError(f"Meal plan is missing required meal: {meal_key}")
		_validate_meal_dict(raw_meal, meal_key)
		formatted_plan[meal_key] = format_single_meal(raw_meal)

	logger.debug("Meal plan formatted successfully")
	return formatted_plan
