"""Pydantic request models for meal planner endpoints."""

from typing import List

from pydantic import BaseModel, Field, field_validator


class MealRequest(BaseModel):
	"""Request payload for generating a personalized meal plan."""

	age: int = Field(..., ge=15, le=100, description="Age in years")
	sex: str = Field(..., description="Biological sex (male/female)")
	height: float = Field(..., ge=100, le=250, description="Height in centimeters")
	weight: float = Field(..., ge=30, le=300, description="Weight in kilograms")
	diet_type: str = Field(..., description="Diet preference (veg/non_veg/vegan)")
	activity_level: str = Field(
		...,
		description="Activity level (sedentary/lightly_active/moderately_active/very_active)",
	)
	goal: str = Field(..., description="Fitness goal (fat_loss/muscle_gain/maintenance)")
	allergies: List[str] = Field(default_factory=list, description="List of allergens to avoid")

	@field_validator("sex", mode="before")
	@classmethod
	def validate_sex(cls, value: str) -> str:
		normalized = str(value).strip().lower()
		if normalized not in {"male", "female"}:
			raise ValueError("sex must be either 'male' or 'female'")
		return normalized

	@field_validator("diet_type", mode="before")
	@classmethod
	def validate_diet_type(cls, value: str) -> str:
		normalized = str(value).strip().lower()
		canonical_map = {
			"veg": "veg",
			"vegetarian": "veg",
			"vegan": "vegan",
			"non_veg": "non_veg",
			"nonveg": "non_veg",
			"non-veg": "non_veg",
			"non vegetarian": "non_veg",
		}
		if normalized not in canonical_map:
			raise ValueError(
				"diet_type must be one of: veg, non_veg, vegan, vegetarian, non-veg, non vegetarian, nonveg"
			)
		return canonical_map[normalized]

	@field_validator("activity_level", mode="before")
	@classmethod
	def validate_activity_level(cls, value: str) -> str:
		normalized = str(value).strip().lower()
		allowed = {"sedentary", "lightly_active", "moderately_active", "very_active"}
		if normalized not in allowed:
			raise ValueError(
				"activity_level must be one of: sedentary, lightly_active, moderately_active, very_active"
			)
		return normalized

	@field_validator("goal", mode="before")
	@classmethod
	def validate_goal(cls, value: str) -> str:
		normalized = str(value).strip().lower()
		allowed = {"fat_loss", "muscle_gain", "maintenance"}
		if normalized not in allowed:
			raise ValueError("goal must be one of: fat_loss, muscle_gain, maintenance")
		return normalized

	@field_validator("allergies", mode="before")
	@classmethod
	def validate_allergies(cls, value: List[str]) -> List[str]:
		if value is None:
			return []
		if not isinstance(value, list):
			raise ValueError("allergies must be a list of strings")

		normalized_allergies: List[str] = []
		for item in value:
			if not isinstance(item, str):
				raise ValueError("allergies must contain only strings")
			cleaned = item.strip().lower()
			if cleaned:
				normalized_allergies.append(cleaned)
		return normalized_allergies
