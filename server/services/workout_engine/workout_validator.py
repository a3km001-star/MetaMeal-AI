"""Workout-plan validators for structure, volume, and safety constraints."""

import re
from typing import Any, Dict, List


def validate_weekly_structure(weekly_plan: Dict[str, Dict[str, Any]], day_types: List[str]) -> None:
	"""Ensure day_1..day_7 exist with expected day types."""
	for idx in range(7):
		day_key = f"day_{idx+1}"
		if day_key not in weekly_plan:
			raise ValueError(f"Missing {day_key} in weekly plan")
		if weekly_plan[day_key].get("type") != day_types[idx]:
			raise ValueError(
				f"Day type mismatch for {day_key}: expected {day_types[idx]}, got {weekly_plan[day_key].get('type')}"
			)


def validate_llm_exercise_shapes(weekly_plan: Dict[str, Dict[str, Any]]) -> None:
	"""Ensure each exercise has required fields and valid primitive types."""
	reps_pattern = re.compile(r"^\d+\s*-\s*\d+$")
	rest_pattern = re.compile(r"^\d+\s*sec$")

	for day in weekly_plan.values():
		exercises = day.get("exercises", [])
		if not isinstance(exercises, list):
			raise ValueError("Exercises must be a list")

		for exercise in exercises:
			if not isinstance(exercise, dict):
				raise ValueError("Exercise entry must be an object")
			for key in ["exercise", "muscle", "sets", "reps", "rest"]:
				if key not in exercise:
					raise ValueError(f"Exercise missing required field: {key}")

			if not str(exercise["exercise"]).strip():
				raise ValueError("Exercise name cannot be empty")
			if not str(exercise["muscle"]).strip():
				raise ValueError("Muscle cannot be empty")

			sets = int(exercise["sets"])
			if sets <= 0 or sets > 30:
				raise ValueError("Sets must be between 1 and 30")

			reps = str(exercise["reps"]).strip().lower().replace(" ", "")
			if not reps_pattern.match(reps):
				raise ValueError("Reps must be in range format, e.g. 8-12")

			rest = str(exercise["rest"]).strip().lower()
			if not rest_pattern.match(rest):
				raise ValueError("Rest must be in format '<n> sec'")


def validate_llm_output(
	weekly_plan: Dict[str, Dict[str, Any]],
	day_types: List[str],
	allowed_exercises_by_muscle: Dict[str, List[str]],
	required_rep_range: str,
	min_exercises_per_day: int,
	max_exercises_per_day: int,
) -> None:
	"""Validate LLM-generated plan shape and safety constraints before deterministic checks."""
	validate_weekly_structure(weekly_plan, day_types)
	validate_llm_exercise_shapes(weekly_plan)

	for idx in range(7):
		day_key = f"day_{idx+1}"
		day = weekly_plan[day_key]
		exercises = day.get("exercises", [])
		if day.get("type") == "rest":
			if exercises:
				raise ValueError(f"{day_key} is rest day but has exercises")
			continue

		if not exercises:
			raise ValueError(f"{day_key} has empty exercise list")
		if len(exercises) < min_exercises_per_day or len(exercises) > max_exercises_per_day:
			raise ValueError(
				f"{day_key} must have between {min_exercises_per_day} and {max_exercises_per_day} exercises"
			)

		for exercise in exercises:
			muscle = str(exercise.get("muscle", "")).strip().lower()
			name = str(exercise.get("exercise", "")).strip()
			if muscle not in allowed_exercises_by_muscle:
				raise ValueError(f"Unsupported muscle in LLM output: {muscle}")
			if name not in set(allowed_exercises_by_muscle[muscle]):
				raise ValueError(f"Exercise not allowed for {muscle}: {name}")

			reps = str(exercise.get("reps", "")).replace(" ", "")
			if reps != required_rep_range:
				raise ValueError(f"Invalid reps range {exercise.get('reps')}, expected {required_rep_range}")


def validate_non_empty_training_days(weekly_plan: Dict[str, Dict[str, Any]]) -> None:
	"""Ensure every non-rest day has at least one exercise."""
	for day in weekly_plan.values():
		if day.get("type") == "rest":
			continue
		if not day.get("exercises"):
			raise ValueError("Training day has no exercises")


def validate_training_day_exercise_counts(weekly_plan: Dict[str, Dict[str, Any]], min_count: int) -> None:
	"""Ensure each training day stays within an allowed exercise count window."""
	for day in weekly_plan.values():
		if day.get("type") == "rest":
			continue
		count = len(day.get("exercises", []))
		if count < min_count or count > 6:
			raise ValueError(f"Training day must have between {min_count} and 6 exercises, got {count}")


def validate_volume(weekly_plan: Dict[str, Dict[str, Any]], weekly_targets: Dict[str, int]) -> None:
	"""Ensure generated set totals per muscle match target totals."""
	actual: Dict[str, int] = {}

	for day in weekly_plan.values():
		for exercise in day.get("exercises", []):
			muscle = str(exercise.get("muscle", "")).strip().lower()
			sets = int(exercise.get("sets", 0) or 0)
			actual[muscle] = actual.get(muscle, 0) + sets

	for muscle, target in weekly_targets.items():
		if actual.get(muscle, 0) != target:
			raise ValueError(f"Volume mismatch for {muscle}: expected {target}, got {actual.get(muscle, 0)}")


def validate_rest_days(weekly_plan: Dict[str, Dict[str, Any]], training_days: int) -> None:
	"""Ensure number of rest days equals 7 - training_days."""
	rest_days = sum(1 for day in weekly_plan.values() if day.get("type") == "rest")
	expected_rest_days = 7 - int(training_days)
	if rest_days != expected_rest_days:
		raise ValueError(f"Rest day mismatch: expected {expected_rest_days}, got {rest_days}")


def validate_no_excessive_duplicates(weekly_plan: Dict[str, Dict[str, Any]]) -> None:
	"""Avoid excessive same-exercise repetition across week."""
	counts: Dict[str, int] = {}
	for day in weekly_plan.values():
		for exercise in day.get("exercises", []):
			name = str(exercise.get("exercise", "")).strip().lower()
			counts[name] = counts.get(name, 0) + 1

	if any(cnt > 2 for cnt in counts.values()):
		raise ValueError("Exercise duplicated excessively in weekly plan")


def validate_plan(
	weekly_plan: Dict[str, Dict[str, Any]],
	weekly_targets: Dict[str, int],
	training_days: int,
	expected_exercises_per_training_day: int,
) -> None:
	validate_non_empty_training_days(weekly_plan)
	validate_training_day_exercise_counts(weekly_plan, expected_exercises_per_training_day)
	validate_rest_days(weekly_plan, training_days)
	validate_no_excessive_duplicates(weekly_plan)
	validate_volume(weekly_plan, weekly_targets)