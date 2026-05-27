"""Pydantic request/response models for progress logging."""

from typing import Optional

from pydantic import BaseModel, Field


class ProgressLogRequest(BaseModel):
	"""Validated input payload for progress logging."""

	user_id: Optional[str] = None
	date: Optional[str] = None
	weight: Optional[float] = Field(None, gt=0)
	consumed_calories: Optional[float] = Field(None, ge=0)
	notes: Optional[str] = None


class ProgressLogResponse(BaseModel):
	"""Progress log response payload."""

	user_id: str
	date: str
	weight: Optional[float] = None
	consumed_calories: Optional[float] = None
	notes: Optional[str] = None