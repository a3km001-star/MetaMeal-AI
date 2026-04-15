"""Goal/intensity mapping helpers for workout planner."""

from typing import Dict


_GOAL_REP_MAP: Dict[str, str] = {
	"muscle_gain": "8-12",
	"fat_loss": "10-15",
	"maintenance": "8-12",
	"endurance": "15-20",
}


_LEVEL_EXERCISE_COUNT: Dict[str, int] = {
	"beginner": 4,
	"intermediate": 5,
	"advanced": 6,
}


def reps_for_goal(goal: str) -> str:
	"""Return deterministic rep range based on goal."""
	return _GOAL_REP_MAP.get(str(goal).strip().lower(), "8-12")


def exercises_per_day_for_level(level: str) -> int:
	"""Return target exercise count for a training day."""
	return _LEVEL_EXERCISE_COUNT.get(str(level).strip().lower(), 5)


def rest_seconds_for(exercise_type: str) -> str:
	"""Return rest prescription for compound vs isolation movement."""
	if str(exercise_type).strip().lower() == "compound":
		return "120 sec"
	return "60 sec"