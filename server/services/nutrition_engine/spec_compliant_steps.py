"""Specification-Compliant Meal Planning Steps (Steps 2-8).

This module implements the deterministic, step-by-step algorithm from the
meal planning specification. Each function represents one logical step in
the algorithm.

Steps Implemented:
  - STEP 2: Carb Baseline Adjustment
  - STEP 4: Age-Based Scaling
  - STEP 5: Meal Split (Calorie Distribution)
  - STEP 6: Bucket Assignment
  - STEP 7: Validity Check
  - STEP 8: Redistribution (if needed)
"""

from typing import Dict, List, Optional, Set, Tuple, Any


# ============================================================================
# CONSTANTS
# ============================================================================

CARB_BASELINE_KCAL = 390.0
"""Fixed carb baseline from spec: 390 kcal"""

MEAL_SLOTS = ("breakfast", "lunch", "dinner", "snack")
"""Standard 4-meal meal plan slots"""

MEAL_SLOT_CALORIE_DISTRIBUTION = {
    "breakfast": 0.25,
    "lunch": 0.35,
    "dinner": 0.30,
    "snack": 0.10,
}
"""Spec-defined calorie distribution across meals"""

# Age-based multiply factors (spec Step 4)
AGE_MULTIPLY_FACTORS = {
    (15, 18): 1.6,
    (18, 22): 2.0,
    (22, 40): 2.5,
    (40, 50): 2.0,
    (50, 60): 1.8,
    (60, 100): 1.8,  # Default for older ages
}

# Calorie error thresholds for bucket assignment (spec Step 6)
BREAKFAST_CALORIE_TOLERANCE = 0.10  # ±10%
OTHER_MEAL_CALORIE_TOLERANCE = 0.12  # ±12%
PROTEIN_TOLERANCE = 0.20  # ±20%


# ============================================================================
# STEP 2: CARB BASELINE ADJUSTMENT
# ============================================================================


def apply_carb_baseline(total_calories: float) -> float:
    """Apply carb baseline adjustment (STEP 2).

    Subtract fixed 390 kcal carb baseline from total daily calories.
    This represents the baseline carbohydrate requirements.

    Args:
        total_calories: Daily calorie target (kcal)

    Returns:
        Adjusted calorie target with baseline subtracted

    Example:
        >>> apply_carb_baseline(2000)
        1610.0
    """
    adjusted = total_calories - CARB_BASELINE_KCAL
    return round(max(adjusted, 800.0), 2)  # Ensure minimum viable calories


# ============================================================================
# STEP 4: AGE-BASED SCALING
# ============================================================================


def get_age_multiply_factor(age: int) -> float:
    """Get multiply factor for recipe scaling based on age (STEP 4).

    Age ranges from specification:
      15-18 years: 1.6x
      18-22 years: 2.0x
      22-40 years: 2.5x
      40-50 years: 2.0x
      50-60 years: 1.8x
      60+  years: 1.8x

    Args:
        age: User's age in years (15-100)

    Returns:
        Multiply factor for recipe scaling

    Example:
        >>> get_age_multiply_factor(25)
        2.5
        >>> get_age_multiply_factor(45)
        2.0
    """
    for (age_min, age_max), factor in AGE_MULTIPLY_FACTORS.items():
        if age_min <= age < age_max:
            return factor
    return 1.8  # Fallback for ages outside ranges


def scale_recipe_by_factor(recipe: Dict[str, Any], multiply_factor: float) -> Dict[str, Any]:
    """Scale recipe macros by multiply factor (STEP 4).

    Creates a normalized recipe with all nutritional values scaled.
    Preserves recipe metadata and recalculates macro values.

    Args:
        recipe: Recipe dict with Calories, Protein, Carbohydrates, Fat
        multiply_factor: Age-based scaling factor (e.g., 1.6-2.5)

    Returns:
        Scaled recipe dict with updated nutritional values

    Example:
        >>> recipe = {"Calories": 100, "Protein": 10, "Carbohydrates": 15, "Fat": 5}
        >>> scaled = scale_recipe_by_factor(recipe, 2.5)
        >>> scaled["Calories"]
        250.0
    """
    def safe_float(val, default=0.0):
        try:
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    calories = safe_float(recipe.get("Calories", 0))
    protein = safe_float(recipe.get("Protein", 0))
    carbs = safe_float(recipe.get("Carbohydrates", recipe.get("Carbs", 0)))
    fat = safe_float(recipe.get("Fat", 0))

    scaled_recipe = dict(recipe)
    scaled_recipe["Calories"] = round(calories * multiply_factor, 2)
    scaled_recipe["Protein"] = round(protein * multiply_factor, 2)
    scaled_recipe["Carbohydrates"] = round(carbs * multiply_factor, 2)
    scaled_recipe["Fat"] = round(fat * multiply_factor, 2)

    return scaled_recipe


# ============================================================================
# STEP 5: MEAL SPLIT
# ============================================================================


def split_calories_by_meal_slot(
    calorie_target: float,
) -> Dict[str, float]:
    """Split daily calorie target by meal slot (STEP 5).

    Distributes daily calories across 4 meals:
      Breakfast: 25%
      Lunch:     35%
      Dinner:    30%
      Snack:     10%

    Args:
        calorie_target: Daily calorie target (kcal)

    Returns:
        Dict mapping meal slot to calorie target

    Example:
        >>> split = split_calories_by_meal_slot(2000)
        >>> split["breakfast"]
        500.0
        >>> split["lunch"]
        700.0
    """
    return {
        slot: round(calorie_target * ratio, 2)
        for slot, ratio in MEAL_SLOT_CALORIE_DISTRIBUTION.items()
    }


def split_macros_by_meal_slot(
    calorie_targets: Dict[str, float],
    macro_ratios: Dict[str, float],
) -> Dict[str, Dict[str, float]]:
    """Split daily macros by meal slot (STEP 5).

    Allocates protein, carbs, and fat targets proportionally across meals
    based on calorie split.

    Args:
        calorie_targets: Dict mapping meal slot to calorie target
        macro_ratios: Dict with protein_grams, carb_grams, fat_grams for full day

    Returns:
        Dict mapping meal slot to macro targets
            {"breakfast": {"calories": 500, "protein": 50, ...}, ...}

    Example:
        >>> cals = split_calories_by_meal_slot(2000)
        >>> macros = {"protein": 200, "carbs": 150, "fat": 70}
        >>> split = split_macros_by_meal_slot(cals, macros)
        >>> split["breakfast"]["protein"]
        50.0
    """
    total_daily_calories = sum(calorie_targets.values())

    slot_macros = {}
    for slot, slot_calories in calorie_targets.items():
        ratio = slot_calories / total_daily_calories if total_daily_calories > 0 else 0.25

        slot_macros[slot] = {
            "calories": slot_calories,
            "protein": round(macro_ratios.get("protein", 0) * ratio, 2),
            "carbohydrates": round(macro_ratios.get("carbohydrates", 0) * ratio, 2),
            "fat": round(macro_ratios.get("fat", 0) * ratio, 2),
        }

    return slot_macros


# ============================================================================
# STEP 6: BUCKET ASSIGNMENT
# ============================================================================


def calculate_macro_error(
    recipe_value: float,
    target_value: float,
) -> float:
    """Calculate normalized error between recipe and target.

    Formula: error = |target - recipe| / target

    Args:
        recipe_value: Actual macro value from recipe
        target_value: Target macro value for meal slot

    Returns:
        Normalized error (0-1, lower is better)
    """
    if target_value <= 0:
        return 0.0 if recipe_value <= 0 else 1.0

    return abs(target_value - recipe_value) / target_value


def check_calorie_threshold(
    recipe_calories: float,
    slot_calories: float,
    slot_name: str,
) -> bool:
    """Check if recipe meets calorie tolerance for slot (STEP 6).

    Different thresholds for breakfast vs other meals:
      Breakfast: ±10%
      Others: ±12%

    Args:
        recipe_calories: Recipe's calorie value
        slot_calories: Meal slot's target calories
        slot_name: Slot name ("breakfast", "lunch", etc.)

    Returns:
        True if within threshold, False otherwise
    """
    if slot_calories <= 0:
        return False

    tolerance = BREAKFAST_CALORIE_TOLERANCE if slot_name == "breakfast" else OTHER_MEAL_CALORIE_TOLERANCE
    lower_bound = slot_calories * (1 - tolerance)
    upper_bound = slot_calories * (1 + tolerance)

    return lower_bound <= recipe_calories <= upper_bound


def check_protein_threshold(
    recipe_protein: float,
    slot_protein: float,
) -> bool:
    """Check if recipe meets protein tolerance (STEP 6).

    Threshold: ±20%

    Args:
        recipe_protein: Recipe's protein value (grams)
        slot_protein: Meal slot's target protein (grams)

    Returns:
        True if within ±20%, False otherwise
    """
    if slot_protein <= 0:
        return recipe_protein <= 5  # Allow small variance when target near zero

    lower_bound = slot_protein * (1 - PROTEIN_TOLERANCE)
    upper_bound = slot_protein * (1 + PROTEIN_TOLERANCE)

    return lower_bound <= recipe_protein <= upper_bound


def assign_recipe_to_slot(
    recipe: Dict[str, Any],
    slot_targets: Dict[str, Dict[str, float]],
    assigned_slots: Dict[str, Optional[Dict[str, Any]]],
    used_recipes: Set[str],
) -> Optional[str]:
    """Assign recipe to best-fit meal slot (STEP 6).

    Algorithm:
      1. For each available slot (not yet assigned):
         a. Check calorie threshold (±10% breakfast, ±12% others)
         b. Check protein threshold (±20%)
      2. Find slot with minimum calorie error
      3. Prevent duplicate recipe usage
      4. Return slot name or None if no valid assignment

    Args:
        recipe: Recipe dict with Calories, Protein, Carbohydrates, Fat
        slot_targets: Dict mapping slot name to target macros
        assigned_slots: Dict mapping slot name to assigned recipe (or None)
        used_recipes: Set of recipe names already used

    Returns:
        Slot name ("breakfast", "lunch", etc.) or None if no valid assignment

    Example:
        >>> recipe = {"RecipeName": "Oatmeal", "Calories": 505, "Protein": 48, ...}
        >>> targets = {
        ...     "breakfast": {"calories": 500, "protein": 50, ...},
        ...     "lunch": {"calories": 700, "protein": 70, ...}
        ... }
        >>> slot = assign_recipe_to_slot(recipe, targets, {"breakfast": None, "lunch": None}, set())
        >>> slot
        "breakfast"
    """
    def safe_float(val):
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    # Check recipe duplication
    recipe_name = recipe.get("RecipeName", "Unknown")
    if recipe_name in used_recipes:
        return None

    recipe_calories = safe_float(recipe.get("Calories", 0))
    recipe_protein = safe_float(recipe.get("Protein", 0))

    best_slot = None
    best_calorie_error = float("inf")

    # Try to assign to each empty slot
    for slot_name in MEAL_SLOTS:
        # Skip already assigned slots
        if assigned_slots.get(slot_name) is not None:
            continue

        slot_target = slot_targets.get(slot_name, {})
        target_calories = safe_float(slot_target.get("calories", 0))
        target_protein = safe_float(slot_target.get("protein", 0))

        # Check thresholds
        if not check_calorie_threshold(recipe_calories, target_calories, slot_name):
            continue
        if not check_protein_threshold(recipe_protein, target_protein):
            continue

        # Calculate calorie error (primary sorting criterion)
        calorie_error = calculate_macro_error(recipe_calories, target_calories)

        # Select slot with minimum error
        if calorie_error < best_calorie_error:
            best_calorie_error = calorie_error
            best_slot = slot_name

    return best_slot


# ============================================================================
# STEP 7: VALIDITY CHECK
# ============================================================================


def is_plan_valid(assigned_slots: Dict[str, Optional[Dict[str, Any]]]) -> bool:
    """Check if meal plan assigns exactly 1 recipe to each slot (STEP 7).

    Validity: All 4 slots have exactly one recipe assigned.

    Args:
        assigned_slots: Dict mapping slot name to assigned recipe (or None)

    Returns:
        True if all 4 slots have recipes, False otherwise

    Example:
        >>> slots = {
        ...     "breakfast": {"RecipeName": "Oatmeal", ...},
        ...     "lunch": None,  # Missing recipe
        ...     "dinner": {"RecipeName": "Chicken", ...},
        ...     "snack": {"RecipeName": "Apple", ...}
        ... }
        >>> is_plan_valid(slots)
        False
    """
    return all(assigned_slots.get(slot) is not None for slot in MEAL_SLOTS)


# ============================================================================
# STEP 8: REDISTRIBUTION
# ============================================================================


def find_overloaded_and_empty_slots(
    assigned_slots: Dict[str, Optional[Dict[str, Any]]],
) -> Tuple[List[str], List[str]]:
    """Identify empty slots and slots with multiple recipes (if applicable).

    For spec: only 1 recipe per slot allowed, so "overloaded" isn't applicable.
    This function identifies which slots are empty.

    Args:
        assigned_slots: Dict mapping slot name to assigned recipe

    Returns:
        Tuple of (empty_slots, all_slots_with_recipes)

    Example:
        >>> slots = {"breakfast": None, "lunch": {...}, "dinner": None, "snack": {...}}
        >>> empty, filled = find_overloaded_and_empty_slots(slots)
        >>> empty
        ["breakfast", "dinner"]
    """
    empty_slots = [slot for slot in MEAL_SLOTS if assigned_slots.get(slot) is None]
    filled_slots = [slot for slot in MEAL_SLOTS if assigned_slots.get(slot) is not None]

    return empty_slots, filled_slots


def can_redistribute(
    empty_slots: List[str],
    filled_slots: List[str],
) -> bool:
    """Check if redistribution is possible (STEP 8).

    Redistribution possible if:
      - Some slots are empty
      - Some slots are filled

    Args:
        empty_slots: List of empty slot names
        filled_slots: List of filled slot names

    Returns:
        True if redistribution possible, False otherwise
    """
    return len(empty_slots) > 0 and len(filled_slots) > 0


def get_redistribution_target(
    empty_slots: List[str],
    filled_slots: List[str],
) -> Optional[str]:
    """Select target slot for redistribution (STEP 8).

    For simple cases with 1 recipe per slot, only the snack slot can be
    reallocated since it has the smallest requirement.

    Args:
        empty_slots: List of empty slot names
        filled_slots: List of filled slot names

    Returns:
        Name of slot to take from, or None if not recommended

    Example:
        >>> get_redistribution_target(["breakfast", "snack"], ["lunch", "dinner"])
        "snack"  # Snack has smallest calorie requirement
    """
    if "snack" in filled_slots and len(empty_slots) > 0:
        return "snack"  # Snack has 10% requirement, easiest to reallocate
    # In other cases, recommend keeping current assignment
    return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def sort_recipes_for_assignment(
    recipes: List[Dict[str, Any]],
    slot_targets: Dict[str, Dict[str, float]],
) -> List[Dict[str, Any]]:
    """Sort recipes for assignment priority (helper for STEP 6).

    Sort order:
      1. By proximity to average meal calories (closest first)
      2. By protein density (higher first)
      3. By absolute protein (higher first)

    Args:
        recipes: List of recipe dicts
        slot_targets: Dict mapping slot to target macros

    Returns:
        Sorted list of recipes

    Example:
        >>> recipes = [
        ...     {"Calories": 450, "Protein": 40, ...},
        ...     {"Calories": 600, "Protein": 30, ...}
        ... ]
        >>> targets = split_macros_by_meal_slot(...)
        >>> sorted_recipes = sort_recipes_for_assignment(recipes, targets)
    """
    def safe_float(val):
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    avg_slot_calories = sum(slot_targets[s]["calories"] for s in MEAL_SLOTS) / 4
    if avg_slot_calories <= 0:
        avg_slot_calories = 1.0

    def sort_key(recipe):
        calories = safe_float(recipe.get("Calories", 0))
        protein = safe_float(recipe.get("Protein", 0))

        # Primary: distance to average meal calories
        calorie_distance = abs(calories - avg_slot_calories)
        # Secondary: protein density (negated so higher is better)
        protein_density = -(protein / max(calories, 1.0))
        # Tertiary: absolute protein (negated so higher is better)
        absolute_protein = -protein

        return (calorie_distance, protein_density, absolute_protein)

    return sorted(recipes, key=sort_key)
