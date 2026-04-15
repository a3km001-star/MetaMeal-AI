"""Hybrid workout planner: deterministic constraints + LLM generation + validation."""

import logging
from typing import Any, Dict, List, Set

from fastapi import HTTPException

from model.workout_model import WorkoutRequest
from services.workout_engine.goal_mapper import (
    exercises_per_day_for_level,
    reps_for_goal,
    rest_seconds_for,
)
from services.workout_engine.llm_generator import WorkoutLLMError, generate_workout_with_llm
from services.workout_engine.split_builder import build_weekly_day_types
from services.workout_engine.volume_calculator import allocate_sets_to_days, resolve_weekly_targets
from services.workout_engine.workout_formatter import format_weekly_plan
from services.workout_engine.workout_validator import validate_llm_output, validate_plan


logger = logging.getLogger(__name__)
MAX_LLM_GENERATION_RETRIES = 2


EXERCISE_BANK: Dict[str, List[Dict[str, Any]]] = {
    "chest": [
        {"exercise": "Barbell Bench Press", "type": "compound", "equipment": ["gym"], "avoid": ["shoulder", "elbow"]},
        {"exercise": "Incline Dumbbell Press", "type": "compound", "equipment": ["gym", "home"], "avoid": ["shoulder"]},
        {"exercise": "Machine Chest Press", "type": "compound", "equipment": ["gym"], "avoid": ["shoulder"]},
        {"exercise": "Push-Up", "type": "compound", "equipment": ["bodyweight", "home", "gym"], "avoid": ["wrist", "shoulder"]},
        {"exercise": "Cable Chest Fly", "type": "isolation", "equipment": ["gym"], "avoid": ["shoulder"]},
    ],
    "shoulders": [
        {"exercise": "Seated Dumbbell Shoulder Press", "type": "compound", "equipment": ["gym", "home"], "avoid": ["shoulder"]},
        {"exercise": "Arnold Press", "type": "compound", "equipment": ["gym", "home"], "avoid": ["shoulder"]},
        {"exercise": "Cable Lateral Raise", "type": "isolation", "equipment": ["gym"], "avoid": ["shoulder"]},
        {"exercise": "Dumbbell Lateral Raise", "type": "isolation", "equipment": ["gym", "home"], "avoid": ["shoulder"]},
    ],
    "triceps": [
        {"exercise": "Close-Grip Bench Press", "type": "compound", "equipment": ["gym"], "avoid": ["elbow", "shoulder"]},
        {"exercise": "Rope Triceps Pushdown", "type": "isolation", "equipment": ["gym"], "avoid": ["elbow"]},
        {"exercise": "Overhead Cable Triceps Extension", "type": "isolation", "equipment": ["gym"], "avoid": ["elbow", "shoulder"]},
        {"exercise": "Bench Dip", "type": "compound", "equipment": ["bodyweight", "home", "gym"], "avoid": ["shoulder", "elbow", "wrist"]},
    ],
    "back": [
        {"exercise": "Conventional Deadlift", "type": "compound", "equipment": ["gym"], "avoid": ["lower_back"]},
        {"exercise": "Pull-Up", "type": "compound", "equipment": ["gym", "home", "bodyweight"], "avoid": ["shoulder", "elbow"]},
        {"exercise": "Wide-Grip Lat Pulldown", "type": "compound", "equipment": ["gym"], "avoid": ["shoulder"]},
        {"exercise": "Seated Cable Row", "type": "compound", "equipment": ["gym"], "avoid": ["lower_back"]},
        {"exercise": "Single-Arm Dumbbell Row", "type": "compound", "equipment": ["gym", "home"], "avoid": ["lower_back"]},
    ],
    "biceps": [
        {"exercise": "EZ-Bar Curl", "type": "isolation", "equipment": ["gym", "home"], "avoid": ["elbow", "wrist"]},
        {"exercise": "Incline Dumbbell Curl", "type": "isolation", "equipment": ["gym", "home"], "avoid": ["elbow"]},
        {"exercise": "Hammer Curl", "type": "isolation", "equipment": ["gym", "home"], "avoid": ["elbow", "wrist"]},
    ],
    "rear_delts": [
        {"exercise": "Face Pull", "type": "isolation", "equipment": ["gym"], "avoid": ["shoulder"]},
        {"exercise": "Reverse Pec Deck", "type": "isolation", "equipment": ["gym"], "avoid": ["shoulder"]},
        {"exercise": "Bent-Over Rear Delt Raise", "type": "isolation", "equipment": ["gym", "home"], "avoid": ["shoulder", "lower_back"]},
    ],
    "quads": [
        {"exercise": "Barbell Back Squat", "type": "compound", "equipment": ["gym"], "avoid": ["knee", "lower_back"]},
        {"exercise": "Leg Press", "type": "compound", "equipment": ["gym"], "avoid": ["knee"]},
        {"exercise": "Goblet Squat", "type": "compound", "equipment": ["gym", "home"], "avoid": ["knee"]},
        {"exercise": "Bodyweight Split Squat", "type": "compound", "equipment": ["bodyweight", "home", "gym"], "avoid": ["knee"]},
    ],
    "hamstrings": [
        {"exercise": "Romanian Deadlift", "type": "compound", "equipment": ["gym", "home"], "avoid": ["lower_back", "hamstring"]},
        {"exercise": "Seated Leg Curl", "type": "isolation", "equipment": ["gym"], "avoid": ["knee"]},
        {"exercise": "Lying Leg Curl", "type": "isolation", "equipment": ["gym"], "avoid": ["knee"]},
    ],
    "glutes": [
        {"exercise": "Hip Thrust", "type": "compound", "equipment": ["gym", "home"], "avoid": ["lower_back"]},
        {"exercise": "Walking Dumbbell Lunge", "type": "compound", "equipment": ["gym", "home"], "avoid": ["knee", "ankle"]},
        {"exercise": "Glute Bridge", "type": "compound", "equipment": ["bodyweight", "home", "gym"], "avoid": ["lower_back"]},
    ],
    "calves": [
        {"exercise": "Standing Calf Raise", "type": "isolation", "equipment": ["gym", "home", "bodyweight"], "avoid": ["ankle"]},
        {"exercise": "Seated Calf Raise", "type": "isolation", "equipment": ["gym"], "avoid": ["ankle"]},
    ],
}


EXERCISE_SLOT_TEMPLATES: Dict[str, Dict[str, Dict[str, int]]] = {
    "push": {
        "beginner": {"chest": 2, "shoulders": 1, "triceps": 1},
        "intermediate": {"chest": 2, "shoulders": 2, "triceps": 1},
        "advanced": {"chest": 2, "shoulders": 2, "triceps": 2},
    },
    "pull": {
        "beginner": {"back": 2, "biceps": 1, "rear_delts": 1},
        "intermediate": {"back": 2, "biceps": 2, "rear_delts": 1},
        "advanced": {"back": 3, "biceps": 2, "rear_delts": 1},
    },
    "legs": {
        "beginner": {"quads": 1, "hamstrings": 1, "glutes": 1, "calves": 1},
        "intermediate": {"quads": 2, "hamstrings": 1, "glutes": 1, "calves": 1},
        "advanced": {"quads": 2, "hamstrings": 2, "glutes": 1, "calves": 1},
    },
    "upper": {
        "beginner": {"chest": 1, "back": 1, "shoulders": 1, "biceps": 1},
        "intermediate": {"chest": 1, "back": 1, "shoulders": 1, "biceps": 1, "triceps": 1},
        "advanced": {"chest": 1, "back": 1, "shoulders": 1, "biceps": 1, "triceps": 1, "rear_delts": 1},
    },
    "lower": {
        "beginner": {"quads": 1, "hamstrings": 1, "glutes": 1, "calves": 1},
        "intermediate": {"quads": 2, "hamstrings": 1, "glutes": 1, "calves": 1},
        "advanced": {"quads": 2, "hamstrings": 2, "glutes": 1, "calves": 1},
    },
    "full_body": {
        "beginner": {"quads": 1, "back": 1, "chest": 1, "shoulders": 1},
        "intermediate": {"quads": 1, "back": 1, "chest": 1, "shoulders": 1, "hamstrings": 1},
        "advanced": {"quads": 1, "back": 1, "chest": 1, "shoulders": 1, "hamstrings": 1, "biceps": 1},
    },
}


def _injury_tags(injuries: List[str]) -> Set[str]:
    joined = " ".join(str(item).strip().lower() for item in injuries)
    tags = set()
    for token in ["shoulder", "knee", "lower_back", "back", "elbow", "wrist", "ankle", "neck", "hamstring"]:
        if token in joined:
            if token == "back":
                tags.add("lower_back")
            else:
                tags.add(token)
    return tags


def _injury_blocked_keywords(injury_flags: Set[str]) -> List[str]:
    """Return conservative keyword blocks for specific injuries."""
    blocked: List[str] = []
    if "shoulder" in injury_flags:
        blocked.extend(["press", "lateral raise", "face pull", "reverse pec deck", "pull-up"])
    return blocked


def _filtered_candidates(muscle: str, equipment: str, injury_flags: Set[str], used_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    pool = EXERCISE_BANK.get(muscle, [])
    filtered: List[Dict[str, Any]] = []
    blocked_keywords = _injury_blocked_keywords(injury_flags)
    for item in pool:
        if equipment not in item["equipment"]:
            continue
        if any(flag in injury_flags for flag in item.get("avoid", [])):
            continue
        lowered_name = str(item.get("exercise", "")).strip().lower()
        if any(keyword in lowered_name for keyword in blocked_keywords):
            continue
        if used_counts.get(item["exercise"], 0) >= 2:
            continue
        filtered.append(item)
    return filtered


def _split_sets(total_sets: int, slots: int) -> List[int]:
    if slots <= 1:
        return [max(total_sets, 1)]
    base = total_sets // slots
    rem = total_sets % slots
    values = []
    for idx in range(slots):
        values.append(base + (1 if idx < rem else 0))
    return [max(v, 1) for v in values]


def _build_day_exercises_fallback(
    day_type: str,
    day_sets: Dict[str, int],
    req: WorkoutRequest,
    used_counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Deterministic fallback generator used when LLM fails validation."""
    level = req.experience_level
    min_count = exercises_per_day_for_level(level)
    template = EXERCISE_SLOT_TEMPLATES.get(day_type, {}).get(level, {})
    rep_range = reps_for_goal(req.goal)
    injury_flags = _injury_tags(req.injuries)

    muscles = [m for m in template if m in day_sets and day_sets[m] > 0]
    for muscle in day_sets:
        if day_sets[muscle] > 0 and muscle not in muscles:
            muscles.append(muscle)
    if req.focus_muscles:
        focus = [m for m in req.focus_muscles if m in muscles]
        non_focus = [m for m in muscles if m not in focus]
        muscles = focus + non_focus

    planned: List[Dict[str, Any]] = []
    for muscle in muscles:
        slots = max(1, int(template.get(muscle, 1)))
        split_sets = _split_sets(day_sets[muscle], slots)
        candidates = _filtered_candidates(muscle, req.equipment, injury_flags, used_counts)
        if not candidates:
            candidates = [
                {
                    "exercise": f"Safe {muscle.title()} Movement",
                    "type": "compound",
                    "equipment": [req.equipment],
                    "avoid": [],
                }
            ]

        for idx, sets in enumerate(split_sets):
            chosen = candidates[idx % len(candidates)]
            used_counts[chosen["exercise"]] = used_counts.get(chosen["exercise"], 0) + 1
            planned.append(
                {
                    "exercise": chosen["exercise"],
                    "muscle": muscle,
                    "sets": int(sets),
                    "reps": rep_range,
                    "rest": rest_seconds_for(chosen["type"]),
                    "_is_compound": chosen["type"] == "compound",
                }
            )

    if len(planned) < min_count and planned:
        while len(planned) < min_count:
            planned.sort(key=lambda item: item["sets"], reverse=True)
            donor = planned[0]
            if donor["sets"] <= 2:
                break
            new_sets = donor["sets"] // 2
            donor["sets"] = donor["sets"] - new_sets
            planned.append(
                {
                    "exercise": f"{donor['exercise']} (Variant)",
                    "muscle": donor["muscle"],
                    "sets": int(new_sets),
                    "reps": donor["reps"],
                    "rest": donor["rest"],
                    "_is_compound": donor["_is_compound"],
                }
            )

    planned.sort(key=lambda item: (not item["_is_compound"], item["muscle"], item["exercise"]))
    for item in planned:
        item.pop("_is_compound", None)
    return planned


def _allowed_exercises_by_muscle(req: WorkoutRequest) -> Dict[str, List[str]]:
    """Produce safe, equipment-compatible exercise names for LLM constraints."""
    injury_flags = _injury_tags(req.injuries)
    blocked_keywords = _injury_blocked_keywords(injury_flags)
    allowed: Dict[str, List[str]] = {}

    for muscle, pool in EXERCISE_BANK.items():
        names = []
        for item in pool:
            if req.equipment not in item["equipment"]:
                continue
            if any(flag in injury_flags for flag in item.get("avoid", [])):
                continue
            lowered_name = str(item.get("exercise", "")).strip().lower()
            if any(keyword in lowered_name for keyword in blocked_keywords):
                continue
            names.append(item["exercise"])
        if names:
            allowed[muscle] = names
        else:
            # Keep output structurally feasible when strict constraints conflict.
            allowed[muscle] = [f"Safe {muscle.title()} Movement"]

    return allowed


def _build_constraints(
    req: WorkoutRequest,
    day_types: List[str],
    weekly_targets: Dict[str, int],
    set_allocation: Dict[str, Dict[str, int]],
) -> Dict[str, Any]:
    """Build deterministic backend constraints used by the LLM layer."""
    return {
        "goal": req.goal,
        "experience_level": req.experience_level,
        "split": req.split,
        "training_days": req.training_days,
        "weekly_volume_per_muscle": weekly_targets,
        "equipment": req.equipment,
        "injuries": req.injuries,
        "focus_muscles": req.focus_muscles,
        "required_rep_range": reps_for_goal(req.goal),
        "min_exercises_per_day": exercises_per_day_for_level(req.experience_level),
        "max_exercises_per_day": 6,
        "day_types": {f"day_{idx+1}": day_types[idx] for idx in range(7)},
        "set_allocation_by_day": set_allocation,
        "allowed_exercises_by_muscle": _allowed_exercises_by_muscle(req),
    }


def _normalize_llm_plan_to_allocation(
    weekly_plan: Dict[str, Dict[str, Any]],
    constraints: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Deterministically enforce per-day per-muscle set allocation on LLM output."""
    rep_range = constraints["required_rep_range"]
    min_exercises_per_day = int(constraints["min_exercises_per_day"])
    target_exercises_per_day = min_exercises_per_day
    max_exercises_per_day = int(constraints["max_exercises_per_day"])
    day_types: Dict[str, str] = constraints["day_types"]
    set_allocation: Dict[str, Dict[str, int]] = constraints["set_allocation_by_day"]
    allowed_exercises: Dict[str, List[str]] = constraints["allowed_exercises_by_muscle"]

    normalized: Dict[str, Dict[str, Any]] = {}

    for idx in range(1, 8):
        day_key = f"day_{idx}"
        expected_type = day_types.get(day_key, "rest")
        day_payload = weekly_plan.get(day_key, {}) if isinstance(weekly_plan, dict) else {}
        raw_exercises = day_payload.get("exercises", []) if isinstance(day_payload, dict) else []

        if expected_type == "rest":
            normalized[day_key] = {"type": "rest", "exercises": []}
            continue

        day_required = set_allocation.get(day_key, {})
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in raw_exercises if isinstance(raw_exercises, list) else []:
            if not isinstance(item, dict):
                continue
            muscle = str(item.get("muscle", "")).strip().lower()
            if muscle not in day_required or int(day_required.get(muscle, 0)) <= 0:
                continue
            grouped.setdefault(muscle, []).append(
                {
                    "exercise": str(item.get("exercise", "")).strip(),
                    "muscle": muscle,
                    "sets": int(item.get("sets", 1) or 1),
                    "reps": str(item.get("reps", rep_range)).replace(" ", ""),
                    "rest": str(item.get("rest", "90 sec")).strip(),
                }
            )

        normalized_exercises: List[Dict[str, Any]] = []
        for muscle, required_sets in day_required.items():
            if required_sets <= 0:
                continue

            candidates = grouped.get(muscle, [])
            if not candidates:
                exercise_name = allowed_exercises.get(muscle, [f"Safe {muscle.title()} Movement"])[0]
                candidates = [
                    {
                        "exercise": exercise_name,
                        "muscle": muscle,
                        "sets": required_sets,
                        "reps": rep_range,
                        "rest": "90 sec",
                    }
                ]

            split = _split_sets(required_sets, len(candidates))
            for ex_idx, item in enumerate(candidates):
                safe_name = item["exercise"]
                if safe_name not in set(allowed_exercises.get(muscle, [])):
                    safe_name = allowed_exercises.get(muscle, [safe_name])[0]
                normalized_exercises.append(
                    {
                        "exercise": safe_name,
                        "muscle": muscle,
                        "sets": int(split[ex_idx]),
                        "reps": rep_range,
                        "rest": item["rest"] if item["rest"] else "90 sec",
                    }
                )

        # Ensure day exercise count window while preserving total per-muscle sets.
        while len(normalized_exercises) < min_exercises_per_day and normalized_exercises:
            donor = max(normalized_exercises, key=lambda item: int(item["sets"]))
            donor_sets = int(donor["sets"])
            if donor_sets <= 1:
                break

            clone_sets = donor_sets // 2
            donor["sets"] = donor_sets - clone_sets

            muscle = str(donor["muscle"])
            allowed = allowed_exercises.get(muscle, [str(donor["exercise"])])
            used_names = [str(item["exercise"]) for item in normalized_exercises if item.get("muscle") == muscle]
            clone_name = next((name for name in allowed if name not in used_names), allowed[0])

            normalized_exercises.append(
                {
                    "exercise": clone_name,
                    "muscle": muscle,
                    "sets": int(clone_sets),
                    "reps": rep_range,
                    "rest": donor.get("rest", "90 sec"),
                }
            )

        while len(normalized_exercises) > target_exercises_per_day and normalized_exercises:
            # Merge two smallest-set exercises, preferring same-muscle merge to preserve distribution logic.
            normalized_exercises.sort(key=lambda item: int(item["sets"]))
            merge_idx_a = 0
            merge_idx_b = 1

            found_same_muscle = False
            for i in range(len(normalized_exercises)):
                for j in range(i + 1, len(normalized_exercises)):
                    if normalized_exercises[i]["muscle"] == normalized_exercises[j]["muscle"]:
                        merge_idx_a, merge_idx_b = i, j
                        found_same_muscle = True
                        break
                if found_same_muscle:
                    break

            a = normalized_exercises[merge_idx_a]
            b = normalized_exercises[merge_idx_b]
            a["sets"] = int(a["sets"]) + int(b["sets"])
            del normalized_exercises[merge_idx_b]

        normalized[day_key] = {
            "type": expected_type,
            "exercises": normalized_exercises,
        }

    return normalized


def _generate_deterministic_fallback(
    req: WorkoutRequest,
    day_types: List[str],
    weekly_targets: Dict[str, int],
    set_allocation: Dict[str, Dict[str, int]],
) -> Dict[str, Any]:
    """Build a deterministic plan if LLM is unavailable or output is invalid."""
    used_counts: Dict[str, int] = {}
    day_exercises: Dict[str, List[Dict[str, Any]]] = {}
    for idx, day_type in enumerate(day_types):
        day_key = f"day_{idx+1}"
        if day_type == "rest":
            day_exercises[day_key] = []
            continue
        day_exercises[day_key] = _build_day_exercises_fallback(
            day_type=day_type,
            day_sets=set_allocation.get(day_key, {}),
            req=req,
            used_counts=used_counts,
        )

    weekly_plan = format_weekly_plan(day_types, day_exercises)
    validate_plan(
        weekly_plan=weekly_plan,
        weekly_targets=weekly_targets,
        training_days=req.training_days,
        expected_exercises_per_training_day=exercises_per_day_for_level(req.experience_level),
    )
    return {"weekly_plan": weekly_plan}


def create_workout_plan_response(request: WorkoutRequest) -> Dict[str, Any]:
    """Generate workout plan via LLM with deterministic constraints and validation."""
    try:
        day_types = build_weekly_day_types(request.split, request.training_days)
        weekly_targets = resolve_weekly_targets(request.weekly_volume_per_muscle, day_types)
        set_allocation = allocate_sets_to_days(day_types, weekly_targets)
        constraints = _build_constraints(request, day_types, weekly_targets, set_allocation)

        last_error: str = ""
        for attempt in range(1, MAX_LLM_GENERATION_RETRIES + 1):
            try:
                llm_payload = generate_workout_with_llm(constraints)
                weekly_plan = llm_payload.get("weekly_plan", {})
                if not isinstance(weekly_plan, dict):
                    raise ValueError("LLM output missing 'weekly_plan' object")

                weekly_plan = _normalize_llm_plan_to_allocation(weekly_plan, constraints)

                validate_llm_output(
                    weekly_plan=weekly_plan,
                    day_types=day_types,
                    allowed_exercises_by_muscle=constraints["allowed_exercises_by_muscle"],
                    required_rep_range=constraints["required_rep_range"],
                    min_exercises_per_day=constraints["min_exercises_per_day"],
                    max_exercises_per_day=constraints["max_exercises_per_day"],
                )

                validate_plan(
                    weekly_plan=weekly_plan,
                    weekly_targets=weekly_targets,
                    training_days=request.training_days,
                    expected_exercises_per_training_day=exercises_per_day_for_level(request.experience_level),
                )

                return {"weekly_plan": weekly_plan}
            except (WorkoutLLMError, ValueError, KeyError) as exc:
                last_error = str(exc)
                logger.warning("LLM workout generation attempt %s failed: %s", attempt, last_error)

        logger.warning("Falling back to deterministic workout generator after LLM failures: %s", last_error)
        return _generate_deterministic_fallback(request, day_types, weekly_targets, set_allocation)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to generate workout plan: {exc}")
