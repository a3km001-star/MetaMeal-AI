"""Deterministic cross-module synchronization checks for meal/workout outputs."""

from typing import Any, Dict, List, Tuple

from model.sync_model import SyncCheckRequest, SyncCheckResponse


def _parse_rep_band(rep_range: str) -> Tuple[int, int]:
    raw = str(rep_range or "").strip().replace(" ", "")
    if "-" not in raw:
        return (0, 0)
    lo, hi = raw.split("-", 1)
    try:
        return (int(lo), int(hi))
    except ValueError:
        return (0, 0)


def _workout_load_metrics(weekly_plan: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    training_days = 0
    total_sets = 0

    for day in weekly_plan.values():
        day_type = str(day.get("type", "")).strip().lower()
        exercises = day.get("exercises", [])
        if day_type == "rest":
            continue
        if isinstance(exercises, list) and exercises:
            training_days += 1
            for ex in exercises:
                try:
                    total_sets += int(ex.get("sets", 0) or 0)
                except (TypeError, ValueError):
                    continue

    return {
        "training_days": training_days,
        "total_sets": total_sets,
    }


def _expected_goal_rep_band(goal: str) -> Tuple[int, int]:
    g = str(goal).strip().lower()
    if g == "muscle_gain":
        return (8, 12)
    if g == "fat_loss":
        return (10, 15)
    if g == "endurance":
        return (15, 20)
    return (8, 12)


def evaluate_sync(payload: SyncCheckRequest) -> SyncCheckResponse:
    mismatches: List[str] = []
    observations: List[str] = []

    goal = str(payload.user_profile.goal).strip().lower()
    weight = float(payload.user_profile.weight)

    calories = float(payload.meal_plan_output.calorie_target)
    protein = float(payload.meal_plan_output.macros.get("protein", 0) or 0)

    metrics = _workout_load_metrics(payload.workout_plan_output.weekly_plan)
    training_days = metrics["training_days"]
    total_sets = metrics["total_sets"]

    # Deterministic nutrition-vs-load guardrails.
    high_load = training_days >= 5 or total_sets >= 75
    moderate_load = training_days >= 4 or total_sets >= 55

    if high_load and calories < 1800:
        mismatches.append("High workout load with low calorie target (<1800 kcal).")
    elif moderate_load and calories < 1600:
        mismatches.append("Moderate workout load with very low calorie target (<1600 kcal).")

    protein_per_kg = protein / max(weight, 1e-6)
    if high_load and protein_per_kg < 1.8:
        mismatches.append("Protein intake is low for high training volume (<1.8 g/kg).")
    elif moderate_load and protein_per_kg < 1.6:
        mismatches.append("Protein intake may be low for training volume (<1.6 g/kg).")

    # Goal-intent checks.
    if goal == "fat_loss" and calories > 3200:
        mismatches.append("Fat-loss goal paired with unusually high calorie target.")
    if goal == "muscle_gain" and calories < 1600:
        mismatches.append("Muscle-gain goal paired with low calorie target.")

    # Goal-to-rep-range checks across weekly exercises.
    expected_lo, expected_hi = _expected_goal_rep_band(goal)
    bad_rep_entries = 0
    total_rep_entries = 0

    for day in payload.workout_plan_output.weekly_plan.values():
        for ex in day.get("exercises", []) if isinstance(day.get("exercises", []), list) else []:
            lo, hi = _parse_rep_band(str(ex.get("reps", "")))
            if lo <= 0 or hi <= 0:
                continue
            total_rep_entries += 1
            if lo != expected_lo or hi != expected_hi:
                bad_rep_entries += 1

    if total_rep_entries > 0 and bad_rep_entries > 0:
        mismatches.append(
            f"Workout rep ranges conflict with goal mapping ({bad_rep_entries}/{total_rep_entries} entries)."
        )

    observations.append(f"Training days detected: {training_days}")
    observations.append(f"Total sets detected: {total_sets}")
    observations.append(f"Protein per kg: {protein_per_kg:.2f}")

    score = max(0, 100 - (len(mismatches) * 20))
    return SyncCheckResponse(
        synchronized=len(mismatches) == 0,
        score=score,
        mismatches=mismatches,
        observations=observations,
    )
