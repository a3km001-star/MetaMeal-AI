"""Routes for meal planner APIs."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends

from controllers.meal_controller import generate_meal_plan_controller
from model.meal_model import MealRequest
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
