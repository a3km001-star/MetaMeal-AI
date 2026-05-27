"""Routes for progress logging APIs."""

import logging

from fastapi import APIRouter

from controllers.progress_controller import get_progress_controller, log_progress_controller
from model.progress_model import ProgressLogRequest


logger = logging.getLogger(__name__)

progress_router = APIRouter(tags=["progress"])


@progress_router.post("/log")
def log_progress(request: ProgressLogRequest):
	"""Log daily progress (weight, calories, notes)."""
	logger.info("POST /progress/log called")
	return log_progress_controller(request)


@progress_router.get("/{user_id}")
def get_progress(user_id: str):
	"""Fetch recent progress history for a user."""
	logger.info("GET /progress/%s called", user_id)
	return get_progress_controller(user_id)
