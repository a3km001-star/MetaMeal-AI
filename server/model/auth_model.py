import re
from datetime import date, datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


def _validate_email(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Email must be a string")

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        raise ValueError("Invalid email address")

    return value.lower()


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, description="The full name of the user")
    email: str = Field(..., description="A valid email address")
    password: str = Field(..., min_length=8, description="A secure password with at least 8 characters")

    _normalize_email = field_validator("email", mode="before")(_validate_email)


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="A valid email address")
    password: str = Field(..., min_length=8)

    _normalize_email = field_validator("email", mode="before")(_validate_email)


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime
    user_details: Optional[Dict[str, Any]] = None
    first_meal_generation: Optional[Dict[str, Any]] = None
    last_meal_generation_date: Optional[date] = None
    meal_generation_streak: int = 0


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
