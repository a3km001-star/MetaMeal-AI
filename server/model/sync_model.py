"""Models for cross-module synchronization checks."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SyncUserProfile(BaseModel):
    goal: str
    weight: float = Field(..., gt=0)
    activity_level: Optional[str] = None


class SyncMealInput(BaseModel):
    calorie_target: float = Field(..., gt=0)
    macros: Dict[str, float]


class SyncWorkoutInput(BaseModel):
    weekly_plan: Dict[str, Dict[str, Any]]


class SyncProgressInput(BaseModel):
    compliance_score: Optional[float] = None
    fatigue_score: Optional[float] = None


class SyncCheckRequest(BaseModel):
    user_profile: SyncUserProfile
    meal_plan_output: SyncMealInput
    workout_plan_output: SyncWorkoutInput
    progress_data: Optional[SyncProgressInput] = None


class SyncCheckResponse(BaseModel):
    synchronized: bool
    score: int
    mismatches: List[str]
    observations: List[str]
