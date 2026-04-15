"""Routes for workout planner APIs."""

import logging

from fastapi import APIRouter

from controllers.workout_controller import generate_workout_plan_controller
from model.workout_model import WorkoutRequest


logger = logging.getLogger(__name__)

workout_router = APIRouter(tags=["workout"])


@workout_router.post("/generate")
def generate_workout_plan(request: WorkoutRequest):
	"""Generate and return a fully validated weekly workout plan."""
	logger.info("POST /workout/generate called")
	return generate_workout_plan_controller(request)
