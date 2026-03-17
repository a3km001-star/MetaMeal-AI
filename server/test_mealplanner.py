"""Standalone local runner for the nutrition meal planner pipeline.

Run from the server folder:
    python test_mealplanner.py
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import HTTPException

from services.nutrition_engine.meal_planner import (
    ActivityLevel,
    FitnessGoal,
    Sex,
    UserProfile,
    create_meal_plan,
)
from utils.helpers import (
    calculate_calorie_totals,
    calculate_macro_totals,
    load_food_dataset,
    normalize_meal_structure,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


SUPPORTED_DIET_TYPES = {"veg", "vegetarian", "non_veg", "non-veg", "nonveg", "vegan"}


def build_sample_profile() -> UserProfile:
    """Create the sample user profile for local pipeline testing."""
    return UserProfile(
        age=24,
        sex=Sex.MALE,
        height=175,
        weight=82,
        diet_type="veg",
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=FitnessGoal.FAT_LOSS,
        allergies=[],
    )


def validate_supported_diet_type(diet_type: str) -> None:
    """Raise a clear error if an unsupported diet type is provided."""
    if diet_type.strip().lower() not in SUPPORTED_DIET_TYPES:
        raise ValueError("Invalid diet type")


def ensure_dataset_ready() -> None:
    """Verify dataset availability before running planner."""
    logger.info("Dataset loading started")
    foods = load_food_dataset()
    if not foods:
        raise ValueError("Food dataset is empty")
    logger.info("Dataset loaded successfully")


def extract_meal_plan_payload(plan: Any) -> Dict[str, Any]:
    """Build a printable meal-plan payload from planner output."""
    logger.info("Meal selection process started")

    normalized = normalize_meal_structure(plan.meal_plan)

    for meal in getattr(plan, "meals", []):
        slot, _, display_name = meal.name.partition(" - ")
        slot_key = slot.strip().lower()
        if slot_key not in {"breakfast", "lunch", "dinner", "snack"}:
            continue

        existing = normalized.get(slot_key, {})
        normalized[slot_key] = {
            **existing,
            "name": existing.get("name") or display_name or meal.name,
            "calories": float(meal.calories),
            "protein": float(meal.protein),
            "carbs": float(meal.carbohydrates),
            "fat": float(meal.fat),
        }

    supplements_payload = []
    for supplement in getattr(plan, "supplements", []):
        supplements_payload.append(
            {
                "name": supplement.name,
                "protein": float(supplement.protein),
                "carbs": float(supplement.carbohydrates),
                "fat": float(supplement.fat),
                "calories": float(supplement.calories),
            }
        )

    normalized["supplements"] = supplements_payload

    return normalized


def print_meal_report(plan: Any, normalized_plan: Dict[str, Any]) -> None:
    """Print formatted output for local inspection."""
    macro_totals = calculate_macro_totals(normalized_plan)
    calorie_total = calculate_calorie_totals(normalized_plan)

    print(f"Calorie Target: {int(round(plan.calorie_target))} kcal")
    print()
    print("Macros:")
    print(f"Protein: {int(round(macro_totals['protein']))} g")
    print(f"Carbs: {int(round(macro_totals['carbs']))} g")
    print(f"Fat: {int(round(macro_totals['fat']))} g")
    print()
    print("Meal Plan")
    print()

    for slot in ("breakfast", "lunch", "dinner", "snack"):
        meal = normalized_plan.get(slot, {})
        meal_name = meal.get("name", "Not generated")
        calories = int(round(float(meal.get("calories", 0) or 0)))

        print(f"{slot.capitalize()}:")
        print(meal_name)
        print(f"Calories: {calories}")
        print()

    supplements = normalized_plan.get("supplements", [])
    if supplements:
        for supplement in supplements:
            name = supplement.get("name", "Supplement")
            protein = int(round(float(supplement.get("protein", 0) or 0)))
            calories = int(round(float(supplement.get("calories", 0) or 0)))
            print("Supplement:")
            print(name)
            print(f"Protein: {protein}g")
            print(f"Calories: {calories}")
            print()

    print(f"Total Daily Calories (meals + supplements): {calorie_total} kcal")


def run_local_test() -> None:
    """Execute the complete meal planner pipeline locally."""
    profile = build_sample_profile()
    validate_supported_diet_type(profile.diet_type or "")

    ensure_dataset_ready()

    try:
        plan = create_meal_plan(profile)
        logger.info("Meal plan generated")

        normalized_plan = extract_meal_plan_payload(plan)

        if normalized_plan.get("supplements"):
            logger.info("Supplement addition completed")

        print_meal_report(plan, normalized_plan)
        logger.info("Successful meal generation")

    except HTTPException as exc:
        detail_text = str(exc.detail).lower()

        if "no foods available after applying diet and allergy filters" in detail_text:
            raise RuntimeError("No meals available after filtering") from exc

        if "no valid meal plan generated" in detail_text:
            logger.warning("Validation failed, regenerating")
            raise RuntimeError("Unable to generate valid meal plan") from exc

        if "dataset" in detail_text or "failed to load food dataset" in detail_text:
            raise ValueError("Food dataset is empty") from exc

        raise RuntimeError(f"Meal planner failed: {exc.detail}") from exc


if __name__ == "__main__":
    try:
        run_local_test()
    except (ValueError, RuntimeError) as err:
        logger.error(str(err))
    except Exception:
        logger.exception("Unexpected error while running local meal planner test")
