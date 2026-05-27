"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.mongo import test_connection
from model.auth_model import UserResponse
from routes.auth import auth_router
from routes.chat import chat_router
from routes.meal import meal_router
from routes.progress import progress_router
from routes.sync import sync_router
from routes.workout import workout_router
from services.auth_service import get_current_user


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

# Configure CORS
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # <--- Change this to allow all origins
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router, prefix="/chat")
app.include_router(meal_router, prefix="/meal")
app.include_router(progress_router, prefix="/progress")
app.include_router(workout_router, prefix="/workout")
app.include_router(sync_router, prefix="/sync")


@app.get("/health")
def health_check():
	"""Simple health endpoint for service monitoring."""
	return {"status": "ok"}


@app.get("/me", response_model=UserResponse)
def read_current_user(current_user: UserResponse = Depends(get_current_user)):
	"""Return authenticated user details for frontend state."""
	return current_user
