"""Routes for workout planner APIs."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends

from controllers.workout_controller import generate_workout_plan_controller, get_latest_workout_plan_controller
from model.workout_model import WorkoutRequest
from services.auth_service import get_current_user_optional


logger = logging.getLogger(__name__)

workout_router = APIRouter(tags=["workout"])


@workout_router.post("/generate")
def generate_workout_plan(
	request: WorkoutRequest,
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Generate and return a fully validated weekly workout plan."""
	logger.info("POST /workout/generate called")
	return generate_workout_plan_controller(request, current_user)


@workout_router.get("/latest")
def get_latest_workout_plan(
	current_user: Optional[dict] = Depends(get_current_user_optional),
):
	"""Retrieve the latest workout plan for the current user."""
	logger.info("GET /workout/latest called")
	return get_latest_workout_plan_controller(current_user)
