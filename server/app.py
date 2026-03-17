"""FastAPI application entry point."""

import logging

from fastapi import FastAPI

from routes.meal import meal_router


logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
	title="Nutrition Meal Planner API",
	version="1.0.0",
	description="API for generating personalized meal plans",
)

app.include_router(meal_router, prefix="/meal")


@app.get("/health")
def health_check():
	"""Simple health endpoint for service monitoring."""
	return {"status": "ok"}
