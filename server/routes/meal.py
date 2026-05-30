"""Routes for meal planner APIs."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends

from controllers.meal_controller import (
	generate_meal_plan_controller,
	save_meal_controller,
	get_saved_meal_for_today_controller,
	save_weight_entry_controller,
	get_weight_history_controller,
	get_meal_history_controller,
	get_weekly_summary_controller,
)
from model.meal_model import MealRequest, SaveMealRequest, WeightRequest
from services.auth_service import get_current_user_optional


logger = logging.getLogger(__name__)

meal_router = APIRouter(tags=["meal"])


@meal_router.post("/generate")
def generate_meal_plan(
	request: MealRequest,
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Generate and return a fully validated meal plan."""
	logger.info("POST /meal/generate called")
	return generate_meal_plan_controller(request, current_user)


@meal_router.post("/save")
def save_meal(
	request: SaveMealRequest,
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Save a generated meal plan to user's profile."""
	logger.info("POST /meal/save called")
	return save_meal_controller(request, current_user)


@meal_router.get("/saved-for-today")
def get_saved_meal_today(
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Get the saved meal for today (if exists)."""
	logger.info("GET /meal/saved-for-today called")
	return get_saved_meal_for_today_controller(current_user)


@meal_router.post("/weight")
def save_weight(
	request: WeightRequest,
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Save a weight entry for the user."""
	logger.info("POST /meal/weight called")
	return save_weight_entry_controller(request.weight, current_user)


@meal_router.get("/weight-history")
def get_weight_history(
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Get user's weight history."""
	logger.info("GET /meal/weight-history called")
	return get_weight_history_controller(current_user)


@meal_router.get("/meal-history")
def get_meal_history(
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Get user's meal history with nutrition data."""
	logger.info("GET /meal/meal-history called")
	return get_meal_history_controller(current_user)


@meal_router.get("/weekly-summary")
def get_weekly_summary(
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Get weekly summary stats for past 7 days."""
	logger.info("GET /meal/weekly-summary called")
	return get_weekly_summary_controller(current_user)
