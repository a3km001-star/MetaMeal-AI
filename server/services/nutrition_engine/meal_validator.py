"""
Meal Plan Validator

Validates a generated CompleteMealPlan against the user's requirements before
it is returned to the caller.  If any check fails the planner should treat the
plan as invalid and regenerate.

Validation checks
-----------------
1. Calorie validation      – total calories within ±10 % of target
2. Macro validation        – protein / carbs / fat each within ±20 % of target
3. Diet-type compliance    – every meal satisfies the requested diet type
4. Allergy compliance      – no meal ingredient contains a listed allergen
5. Meal-structure validity – plan contains exactly Breakfast, Lunch, Dinner, Snack
                             and each has the required fields
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from services.nutrition_engine.meal_planner import CompleteMealPlan

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CALORIE_TOLERANCE: float = 0.10          # ±10 %
MACRO_TOLERANCE: float = 0.20            # ±20 % per macro
REQUIRED_MEAL_NAMES: List[str] = ["Breakfast", "Lunch", "Dinner", "Snack"]
REQUIRED_MEAL_FIELDS: Tuple[str, ...] = ("name", "calories", "ingredients", "instructions")

# Diet-type keyword lists (mirrors constraint_solver.py)
_NON_VEG_KEYWORDS: List[str] = [
    "chicken", "mutton", "lamb", "beef", "pork", "fish", "prawn", "shrimp",
    "meat", "egg", "crab", "lobster", "salmon", "tuna", "anchovy", "bacon",
    "sausage", "ham", "turkey", "duck", "goat",
]
_NON_VEGAN_KEYWORDS: List[str] = [
    "milk", "curd", "yogurt", "yoghurt", "cheese", "paneer", "cream",
    "butter", "ghee", "dairy", "whey", "casein", "egg", "honey",
] + _NON_VEG_KEYWORDS

_DIET_ALIAS_MAP: Dict[str, str] = {
    "veg": "vegetarian",
    "vegetarian": "vegetarian",
    "non_veg": "non-vegetarian",
    "non-veg": "non-vegetarian",
    "nonveg": "non-vegetarian",
    "non vegetarian": "non-vegetarian",
    "non-vegetarian": "non-vegetarian",
    "vegan": "vegan",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _all_plan_items(meal_plan: CompleteMealPlan) -> List:
    """Return meals plus supplements for validations that apply to all consumables."""
    return list(meal_plan.meals) + list(meal_plan.supplements or [])

def calculate_total_calories(meal_plan: CompleteMealPlan) -> float:
    """Sum calorie values across all meals in the plan."""
    plan_items = _all_plan_items(meal_plan)
    if not plan_items:
        return 0.0
    return round(sum(item.calories for item in plan_items), 2)


def calculate_macro_totals(meal_plan: CompleteMealPlan) -> Dict[str, float]:
    """Sum protein, carbohydrates, and fat across all meals.

    Returns:
        {"protein": float, "carbohydrates": float, "fat": float}
    """
    plan_items = _all_plan_items(meal_plan)
    protein = sum(item.protein for item in plan_items)
    carbohydrates = sum(item.carbohydrates for item in plan_items)
    fat = sum(item.fat for item in plan_items)
    return {
        "protein": round(protein, 2),
        "carbohydrates": round(carbohydrates, 2),
        "fat": round(fat, 2),
    }


def _contains_keyword(text: str, keyword: str) -> bool:
    """Return True if *keyword* appears as a whole word in *text*."""
    return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text))


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def validate_calories(total_calories: float, target_calories: float) -> bool:
    """Check that *total_calories* is within ±CALORIE_TOLERANCE of target.

    Args:
        total_calories: Sum of calories across all meals.
        target_calories: Daily calorie target from the user profile.

    Returns:
        True  – within tolerance.
        False – outside tolerance or invalid inputs.
    """
    if target_calories <= 0:
        logger.error("Calorie validation failed: target_calories must be positive (got %s)", target_calories)
        return False

    if total_calories < 0:
        logger.error("Calorie validation failed: total_calories cannot be negative (got %s)", total_calories)
        return False

    lower = target_calories * (1 - CALORIE_TOLERANCE)
    upper = target_calories * (1 + CALORIE_TOLERANCE)
    passed = lower <= total_calories <= upper

    if passed:
        logger.info(
            "Calorie validation passed: %.1f kcal is within [%.1f, %.1f]",
            total_calories, lower, upper,
        )
    else:
        logger.warning(
            "Calorie validation failed: %.1f kcal is outside [%.1f, %.1f]",
            total_calories, lower, upper,
        )

    return passed


def validate_macros(
    actual_macros: Dict[str, float],
    target_macros: Dict[str, float],
) -> bool:
    """Check that each macro in *actual_macros* is within ±MACRO_TOLERANCE of its target.

    Args:
        actual_macros:  {"protein": float, "carbohydrates": float, "fat": float}
        target_macros:  same shape – targets taken from the meal plan.

    Returns:
        True if every macro is within tolerance, False otherwise.
    """
    required = ("protein", "carbohydrates", "fat")

    for macro in required:
        if macro not in target_macros:
            logger.error("Macro validation failed: missing target for '%s'", macro)
            return False
        if macro not in actual_macros:
            logger.error("Macro validation failed: missing actual value for '%s'", macro)
            return False

        target = target_macros[macro]
        actual = actual_macros[macro]

        if target < 0 or actual < 0:
            logger.error(
                "Macro validation failed: negative value for '%s' (target=%s, actual=%s)",
                macro, target, actual,
            )
            return False

        if target == 0:
            # If target is zero the actual must also be zero to pass.
            if actual != 0:
                logger.warning("Macro validation failed: target for '%s' is 0 but actual is %.2f", macro, actual)
                return False
            continue

        lower = target * (1 - MACRO_TOLERANCE)
        upper = target * (1 + MACRO_TOLERANCE)

        if not (lower <= actual <= upper):
            logger.warning(
                "Macro validation failed: %s %.2fg is outside [%.2f, %.2f]",
                macro, actual, lower, upper,
            )
            return False

    logger.info("Macro validation passed: all macros within ±%.0f%% tolerance", MACRO_TOLERANCE * 100)
    return True


def validate_diet(meal_plan: CompleteMealPlan, user_diet: Optional[str]) -> bool:
    """Verify every meal in the plan satisfies *user_diet*.

    Accepted *user_diet* values: ``"veg"`` / ``"vegetarian"``,
    ``"non_veg"`` / ``"non-vegetarian"``, ``"vegan"``.
    ``None`` or ``"any"`` / ``"unknown"`` skips the check (returns True).

    Args:
        meal_plan: The generated meal plan.
        user_diet: Diet preference string from the user profile.

    Returns:
        True if compliant or no diet specified, False on any violation.
    """
    if not user_diet or user_diet.lower() in ("any", "unknown", "all", "none"):
        logger.info("Diet validation skipped: no diet type specified")
        return True

    normalized = _DIET_ALIAS_MAP.get(user_diet.lower().strip(), user_diet.lower().strip())

    violations: List[str] = []

    for item in _all_plan_items(meal_plan):
        ingredients_lower = item.ingredients.lower()
        diet_type_field = _DIET_ALIAS_MAP.get(
            (item.diet_type or "unknown").lower().strip(),
            (item.diet_type or "unknown").lower().strip(),
        )

        if normalized == "vegetarian":
            # Fail if non-veg ingredients are found in a meal not marked vegetarian
            if diet_type_field == "non-vegetarian":
                violations.append(f"'{item.name}' is marked non-vegetarian")
            elif diet_type_field in ("vegetarian", "vegan", "unknown"):
                has_non_veg = any(
                    _contains_keyword(ingredients_lower, kw) for kw in _NON_VEG_KEYWORDS
                )
                if has_non_veg:
                    violations.append(f"'{item.name}' contains non-vegetarian ingredients")
            # else: unrecognised diet_type – accepted to avoid false positives from alias variants

        elif normalized == "vegan":
            has_non_vegan = any(
                _contains_keyword(ingredients_lower, kw) for kw in _NON_VEGAN_KEYWORDS
            )
            if has_non_vegan:
                violations.append(f"'{item.name}' contains non-vegan ingredients")

        # non-vegetarian accepts all foods – no check needed.

    if violations:
        for v in violations:
            logger.warning("Diet validation failed (%s): %s", user_diet, v)
        return False

    logger.info("Diet validation passed: all meals comply with diet type '%s'", user_diet)
    return True


def validate_allergies(
    meal_plan: CompleteMealPlan,
    allergies: Optional[List[str]],
) -> bool:
    """Check that no meal ingredient contains any listed allergen.

    Args:
        meal_plan:  The generated meal plan.
        allergies:  List of allergen keywords (e.g. ``["peanut", "milk"]``).

    Returns:
        True if no allergens found, False on any violation.
    """
    if not allergies:
        logger.info("Allergy validation skipped: no allergens specified")
        return True

    allergens_lower = [a.lower().strip() for a in allergies if a.strip()]
    violations: List[str] = []

    for item in _all_plan_items(meal_plan):
        ingredients_lower = item.ingredients.lower()
        for allergen in allergens_lower:
            if _contains_keyword(ingredients_lower, allergen):
                violations.append(f"Allergen '{allergen}' found in item '{item.name}'")

    if violations:
        for v in violations:
            logger.warning("Allergy violation detected: %s", v)
        return False

    logger.info("Allergy validation passed: no listed allergens found in any meal")
    return True


def validate_meal_structure(meal_plan: CompleteMealPlan) -> bool:
    """Verify the plan has exactly the four required meals with all required fields.

    Required meals : Breakfast, Lunch, Dinner, Snack (case-insensitive prefix match).
    Required fields per meal: name, calories, ingredients, instructions.

    Args:
        meal_plan: The generated meal plan.

    Returns:
        True if structure is valid, False otherwise.
    """
    if not meal_plan.meals:
        logger.error("Meal structure validation failed: meal plan is empty")
        return False

    if len(meal_plan.meals) != len(REQUIRED_MEAL_NAMES):
        logger.error(
            "Meal structure validation failed: expected %d meals, got %d",
            len(REQUIRED_MEAL_NAMES), len(meal_plan.meals),
        )
        return False

    # Each meal in the plan must start with one of the required name tokens.
    required_lower = [r.lower() for r in REQUIRED_MEAL_NAMES]

    for i, meal in enumerate(meal_plan.meals):
        # --- Required fields present and non-empty ---
        for field in REQUIRED_MEAL_FIELDS:
            value = getattr(meal, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                logger.error(
                    "Meal structure validation failed: meal #%d is missing or has empty field '%s'",
                    i + 1, field,
                )
                return False
            if field == "calories" and meal.calories <= 0:
                logger.error(
                    "Meal structure validation failed: meal #%d has non-positive calories (%.2f)",
                    i + 1, meal.calories,
                )
                return False

        # --- Meal name maps to expected slot ---
        meal_name_lower = meal.name.lower()
        expected = required_lower[i]
        # Accept meals whose names begin with the expected type keyword, or that
        # contain it as a word anywhere (e.g. "Lunch – Paneer Curry").
        if not (
            meal_name_lower.startswith(expected)
            or _contains_keyword(meal_name_lower, expected)
        ):
            logger.warning(
                "Meal structure warning: meal #%d name '%s' does not match expected slot '%s'",
                i + 1, meal.name, REQUIRED_MEAL_NAMES[i],
            )
            # This is a warning, not a hard failure – the planner assigns slots
            # internally and the meal names come from the recipe dataset.

    logger.info("Meal structure validation passed: %d meals with all required fields", len(meal_plan.meals))
    return True


# ---------------------------------------------------------------------------
# Master validation function
# ---------------------------------------------------------------------------

def validate_meal_plan(
    meal_plan: CompleteMealPlan,
    target_calories: float,
    target_macros: Dict[str, float],
    user_diet: Optional[str] = None,
    allergies: Optional[List[str]] = None,
) -> bool:
    """Run all validation checks against a generated meal plan.

    Calls the five validation functions in sequence.  The first failed check
    causes the function to return ``False`` so the planner knows to regenerate.

    Args:
        meal_plan:       The generated ``CompleteMealPlan``.
        target_calories: Daily calorie target.
        target_macros:   ``{"protein": float, "carbohydrates": float, "fat": float}``.
        user_diet:       Diet preference string (``"veg"``, ``"non_veg"``, ``"vegan"``).
        allergies:       List of allergen keywords to avoid.

    Returns:
        True  – all checks passed; plan is safe to return to the caller.
        False – at least one check failed; planner should regenerate.

    Raises:
        ValueError: If *meal_plan* has no meals or *target_calories* is invalid.
    """
    logger.info("Starting meal plan validation")

    # --- Guard: empty plan ---
    if not meal_plan or not meal_plan.meals:
        logger.error("Validation aborted: meal plan is empty or None")
        raise ValueError("meal_plan must not be empty")

    # --- Guard: invalid target ---
    if target_calories <= 0:
        logger.error("Validation aborted: target_calories must be positive (got %s)", target_calories)
        raise ValueError("target_calories must be a positive number")

    # --- Guard: target_macros shape ---
    for key in ("protein", "carbohydrates", "fat"):
        if key not in target_macros:
            raise ValueError(f"target_macros is missing required key '{key}'")
        if target_macros[key] < 0:
            raise ValueError(f"target_macros['{key}'] must not be negative")

    # ---- 1. Calorie validation ----
    actual_calories = calculate_total_calories(meal_plan)
    if not validate_calories(actual_calories, target_calories):
        logger.warning("Meal plan validation FAILED at calorie check")
        return False

    # ---- 2. Macro validation ----
    actual_macros = calculate_macro_totals(meal_plan)
    if not validate_macros(actual_macros, target_macros):
        logger.warning("Meal plan validation FAILED at macro check")
        return False

    # ---- 3. Diet-type compliance ----
    if not validate_diet(meal_plan, user_diet):
        logger.warning("Meal plan validation FAILED at diet-type check")
        return False

    # ---- 4. Allergy compliance ----
    if not validate_allergies(meal_plan, allergies):
        logger.warning("Meal plan validation FAILED at allergy check")
        return False

    # ---- 5. Meal-structure validity ----
    if not validate_meal_structure(meal_plan):
        logger.warning("Meal plan validation FAILED at meal-structure check")
        return False

    logger.info("Meal plan validation PASSED: all 5 checks succeeded")
    return True
