"""Formatting helpers for workout-plan API response payloads."""

from typing import Any, Dict, List


def format_weekly_plan(day_types: List[str], day_exercises: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
	"""Build strict weekly_plan mapping with day_i keys."""
	weekly_plan: Dict[str, Dict[str, Any]] = {}

	for idx in range(7):
		day_key = f"day_{idx+1}"
		day_type = day_types[idx]
		exercises = day_exercises.get(day_key, [])
		weekly_plan[day_key] = {
			"type": day_type,
			"exercises": exercises,
		}

	return weekly_plan