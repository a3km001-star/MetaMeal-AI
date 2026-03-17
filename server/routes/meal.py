"""Routes for meal planner APIs."""

import logging

from fastapi import APIRouter

from controllers.meal_controller import generate_meal_plan_controller
from model.meal_model import MealRequest


logger = logging.getLogger(__name__)

meal_router = APIRouter(tags=["meal"])


@meal_router.post("/generate")
def generate_meal_plan(request: MealRequest):
	"""Generate and return a fully validated meal plan."""
	logger.info("POST /meal/generate called")
	return generate_meal_plan_controller(request)
