"""Pydantic request/response models for workout planner endpoints."""

from typing import Dict, List, Literal, Union

from pydantic import BaseModel, Field, field_validator


AllowedGoal = Literal["muscle_gain", "fat_loss", "maintenance", "endurance"]
AllowedLevel = Literal["beginner", "intermediate", "advanced"]
AllowedSplit = Literal["push_pull_legs", "upper_lower", "full_body"]
AllowedEquipment = Literal["gym", "home", "bodyweight"]
AllowedDayType = Literal["push", "pull", "legs", "upper", "lower", "full_body", "rest"]


class WorkoutRequest(BaseModel):
	"""Validated input payload for workout generation."""

	goal: AllowedGoal
	experience_level: AllowedLevel
	split: AllowedSplit
	training_days: int = Field(..., ge=1, le=7)
	weekly_volume_per_muscle: Union[int, Dict[str, int]] = Field(...)
	equipment: AllowedEquipment
	injuries: List[str] = Field(default_factory=list)
	focus_muscles: List[str] = Field(default_factory=list)

	@field_validator("weekly_volume_per_muscle", mode="before")
	@classmethod
	def validate_volume(cls, value: Union[int, Dict[str, int]]) -> Union[int, Dict[str, int]]:
		if isinstance(value, int):
			if value <= 0:
				raise ValueError("weekly_volume_per_muscle must be > 0")
			return value

		if isinstance(value, dict):
			cleaned: Dict[str, int] = {}
			for muscle, sets in value.items():
				m = str(muscle).strip().lower()
				if not m:
					continue
				if int(sets) <= 0:
					raise ValueError("weekly_volume_per_muscle dict values must be > 0")
				cleaned[m] = int(sets)
			if not cleaned:
				raise ValueError("weekly_volume_per_muscle dict cannot be empty")
			return cleaned

		raise ValueError("weekly_volume_per_muscle must be int or dict")

	@field_validator("injuries", "focus_muscles", mode="before")
	@classmethod
	def normalize_string_lists(cls, value: List[str]) -> List[str]:
		if value is None:
			return []
		if not isinstance(value, list):
			raise ValueError("Expected a list of strings")
		return [str(item).strip().lower() for item in value if str(item).strip()]


class WorkoutExercise(BaseModel):
	exercise: str
	muscle: str
	sets: int
	reps: str
	rest: str


class WorkoutDay(BaseModel):
	type: AllowedDayType
	exercises: List[WorkoutExercise] = Field(default_factory=list)


class WorkoutPlanResponse(BaseModel):
	weekly_plan: Dict[str, WorkoutDay]
