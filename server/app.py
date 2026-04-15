"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.mongo import test_connection
from routes.meal import meal_router
from routes.sync import sync_router
from routes.workout import workout_router


logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

@asynccontextmanager
async def lifespan(_app: FastAPI):
	"""Validate DB connectivity during application startup."""
	logging.info("Checking MongoDB connection at startup")
	test_connection(raise_on_error=True)
	logging.info("MongoDB connection established")
	yield


app = FastAPI(
	title="Nutrition Meal Planner API",
	version="1.0.0",
	description="API for generating personalized meal plans",
	lifespan=lifespan,
)

app.include_router(meal_router, prefix="/meal")
app.include_router(workout_router, prefix="/workout")
app.include_router(sync_router, prefix="/sync")


@app.get("/health")
def health_check():
	"""Simple health endpoint for service monitoring."""
	return {"status": "ok"}
