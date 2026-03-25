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

import hashlib
import json
import random
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

CALORIE_ERROR_WEIGHT = 0.60
PROTEIN_ERROR_WEIGHT = 0.25
CARB_ERROR_WEIGHT = 0.10
FAT_ERROR_WEIGHT = 0.05
MAX_CANDIDATES_PER_SLOT = 20
MAX_SWAP_OPTIMIZATION_ITERATIONS = 3
RELAXED_CALORIE_TOLERANCE = 0.18
RELAXED_PROTEIN_TOLERANCE = 0.25
RECENT_REPEAT_PENALTY = 0.20
LAST_24H_REPEAT_PENALTY = 0.50
HARD_REPEAT_BLOCK_PENALTY = 10.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def _get_stable_recipe_id(recipe: Dict[str, Any]) -> str:
    """Return a deterministic recipe identifier stable across process lifetimes."""
    explicit_id = recipe.get("RecipeId") or recipe.get("id")
    if explicit_id is not None and str(explicit_id).strip():
        return f"explicit:{str(explicit_id).strip()}"

    payload = {
        "name": recipe.get("RecipeName") or recipe.get("DisplayName") or recipe.get("name") or "",
        "ingredients": recipe.get("Ingredients") or recipe.get("ingredients") or "",
        "instructions": recipe.get("Instructions") or recipe.get("instructions") or "",
        "diet_type": recipe.get("DietType") or recipe.get("diet_type") or "",
        "calories": round(_safe_float(recipe.get("Calories", recipe.get("calories", 0))), 4),
        "protein": round(_safe_float(recipe.get("Protein", recipe.get("protein", 0))), 4),
        "carbohydrates": round(
            _safe_float(recipe.get("Carbohydrates", recipe.get("carbohydrates", recipe.get("Carbs", 0)))),
            4,
        ),
        "fat": round(_safe_float(recipe.get("Fat", recipe.get("fat", 0))), 4),
    }

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    return f"hash:{digest}"


def _get_recipe_name_key(recipe: Dict[str, Any]) -> str:
    return str(recipe.get("RecipeName") or recipe.get("DisplayName") or recipe.get("name") or "").strip().lower()


def _normalize_meal_history(meal_history: Optional[Dict[str, List[str]]]) -> Dict[str, List[str]]:
    normalized: Dict[str, List[str]] = {slot: [] for slot in MEAL_SLOTS}
    if not meal_history:
        return normalized

    for slot in MEAL_SLOTS:
        raw = meal_history.get(slot, [])
        if not isinstance(raw, list):
            continue
        normalized[slot] = [str(item).strip().lower() for item in raw if str(item).strip()]

    return normalized


def _diversity_penalty_for_recipe(recipe: Dict[str, Any], slot: str, history: Dict[str, List[str]], bucket_size: int) -> float:
    """Compute diversity penalty with gradual easing for small datasets."""
    recipe_name = _get_recipe_name_key(recipe)
    if not recipe_name:
        return 0.0

    slot_history = history.get(slot, [])
    penalty = 0.0

    if len(slot_history) >= 2 and slot_history[0] == recipe_name and slot_history[1] == recipe_name:
        penalty += HARD_REPEAT_BLOCK_PENALTY
    elif slot_history and slot_history[0] == recipe_name:
        penalty += LAST_24H_REPEAT_PENALTY
    elif recipe_name in slot_history[1:3]:
        penalty += RECENT_REPEAT_PENALTY

    # Small dataset handling: gradually reduce penalty pressure.
    scale = 1.0
    if bucket_size <= 6:
        scale = 0.6
    if bucket_size <= 3:
        scale = 0.3

    return round(penalty * scale, 6)


def _deterministic_pick_from_top_k(
    scored_candidates: List[Tuple[float, Dict[str, Any]]],
    meal_type: str,
    history: Dict[str, List[str]],
) -> Optional[Dict[str, Any]]:
    """Pick one candidate from top-k using deterministic pseudo-random indexing."""
    if not scored_candidates:
        return None

    sorted_candidates = sorted(
        scored_candidates,
        key=lambda item: (item[0], _get_recipe_name_key(item[1]), _get_stable_recipe_id(item[1])),
    )

    k = min(5, len(sorted_candidates))
    if len(sorted_candidates) >= 3:
        k = max(3, k)
    top_candidates = sorted_candidates[:k]

    seed_payload = {
        "meal_type": meal_type,
        "history": history,
        "candidate_ids": [_get_stable_recipe_id(item[1]) for item in top_candidates],
    }
    seed_text = json.dumps(seed_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    seed_value = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16)
    selected_index = seed_value % len(top_candidates)
    return top_candidates[selected_index][1]


def _score_candidates_for_slot(
    recipes: List[Dict[str, Any]],
    slot: str,
    slot_targets: Dict[str, Dict[str, float]],
    used_recipe_ids: Set[str],
    history: Dict[str, List[str]],
    tolerance_multiplier: float = 1.0,
    custom_calorie_tolerance: Optional[float] = None,
    custom_protein_tolerance: Optional[float] = None,
    allow_hard_repeats: bool = False,
) -> List[Tuple[float, Dict[str, Any]]]:
    """Build final-score candidates for a slot under constraints."""
    slot_target = slot_targets.get(slot, {})
    raw_candidates: List[Dict[str, Any]] = []

    for recipe in recipes:
        rid = _get_stable_recipe_id(recipe)
        if rid in used_recipe_ids:
            continue

        if custom_calorie_tolerance is not None and custom_protein_tolerance is not None:
            recipe_calories = _safe_float(recipe.get("Calories", 0))
            recipe_protein = _safe_float(recipe.get("Protein", 0))
            target_calories = _safe_float(slot_target.get("calories", 0))
            target_protein = _safe_float(slot_target.get("protein", 0))
            if target_calories <= 0:
                continue
            calorie_ok = (
                target_calories * (1 - custom_calorie_tolerance)
                <= recipe_calories
                <= target_calories * (1 + custom_calorie_tolerance)
            )
            if target_protein <= 0:
                protein_ok = recipe_protein <= 5
            else:
                protein_ok = (
                    target_protein * (1 - custom_protein_tolerance)
                    <= recipe_protein
                    <= target_protein * (1 + custom_protein_tolerance)
                )
            if not (calorie_ok and protein_ok):
                continue
        else:
            if not _check_slot_thresholds(recipe, slot_target, slot, tolerance_multiplier=tolerance_multiplier):
                continue

        raw_candidates.append(recipe)

    if not raw_candidates:
        return []

    bucket_size = len(raw_candidates)
    scored: List[Tuple[float, Dict[str, Any]]] = []
    backup_hard_repeat: List[Tuple[float, Dict[str, Any]]] = []

    for recipe in raw_candidates:
        base_error = calculate_weighted_slot_error(recipe, slot_target)
        penalty = _diversity_penalty_for_recipe(recipe, slot, history, bucket_size)
        final_score = round(base_error + penalty, 6)

        if penalty >= HARD_REPEAT_BLOCK_PENALTY and not allow_hard_repeats:
            backup_hard_repeat.append((final_score, recipe))
            continue
        scored.append((final_score, recipe))

    if scored:
        return scored
    return backup_hard_repeat if allow_hard_repeats else []


def select_meals_with_diversity(
    recipes: List[Dict[str, Any]],
    slot_targets: Dict[str, Dict[str, float]],
    meal_history: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Dict[str, Optional[Dict[str, Any]]], Set[str], Dict[str, Any]]:
    """Select meals using diversity-aware scoring and fault-tolerant fallback levels."""
    assigned_slots: Dict[str, Optional[Dict[str, Any]]] = {slot: None for slot in MEAL_SLOTS}
    if not recipes:
        return assigned_slots, set(), {"fallback_level": 5, "reason": "empty_recipe_pool"}

    history = _normalize_meal_history(meal_history)
    used_recipe_ids: Set[str] = set()
    fallback_level_reached = 0

    # STEP A: Primary strict slot selection with diversity-aware top-k deterministic pick.
    for slot in MEAL_SLOTS:
        scored = _score_candidates_for_slot(
            recipes,
            slot,
            slot_targets,
            used_recipe_ids,
            history,
            tolerance_multiplier=1.0,
            allow_hard_repeats=False,
        )
        selected = _deterministic_pick_from_top_k(scored, slot, history)
        if selected is not None:
            assigned_slots[slot] = selected
            used_recipe_ids.add(_get_stable_recipe_id(selected))

    # LEVEL 1: Redistribution.
    if not is_plan_valid(assigned_slots):
        fallback_level_reached = max(fallback_level_reached, 1)
        assigned_slots = redistribute_empty_slots(assigned_slots, recipes, slot_targets, used_recipe_ids)
        used_recipe_ids = {
            _get_stable_recipe_id(recipe)
            for recipe in assigned_slots.values()
            if recipe is not None
        }

    # LEVEL 2: Borrow from other buckets (ignore slot-specific history, keep duplicate prevention).
    if not is_plan_valid(assigned_slots):
        fallback_level_reached = max(fallback_level_reached, 2)
        for slot in MEAL_SLOTS:
            if assigned_slots.get(slot) is not None:
                continue

            borrowed_scored: List[Tuple[float, Dict[str, Any]]] = []
            for donor_slot in MEAL_SLOTS:
                donor_candidates = _score_candidates_for_slot(
                    recipes,
                    donor_slot,
                    slot_targets,
                    used_recipe_ids,
                    history,
                    tolerance_multiplier=1.0,
                    allow_hard_repeats=True,
                )
                for _, recipe in donor_candidates[:MAX_CANDIDATES_PER_SLOT]:
                    borrowed_scored.append((calculate_weighted_slot_error(recipe, slot_targets.get(slot, {})), recipe))

            selected = _deterministic_pick_from_top_k(borrowed_scored, slot, history)
            if selected is not None:
                assigned_slots[slot] = selected
                used_recipe_ids.add(_get_stable_recipe_id(selected))

    # LEVEL 3: Relaxed thresholds (±18% calories, ±25% protein).
    if not is_plan_valid(assigned_slots):
        fallback_level_reached = max(fallback_level_reached, 3)
        for slot in MEAL_SLOTS:
            if assigned_slots.get(slot) is not None:
                continue
            relaxed_scored = _score_candidates_for_slot(
                recipes,
                slot,
                slot_targets,
                used_recipe_ids,
                history,
                custom_calorie_tolerance=RELAXED_CALORIE_TOLERANCE,
                custom_protein_tolerance=RELAXED_PROTEIN_TOLERANCE,
                allow_hard_repeats=True,
            )
            selected = _deterministic_pick_from_top_k(relaxed_scored, slot, history)
            if selected is not None:
                assigned_slots[slot] = selected
                used_recipe_ids.add(_get_stable_recipe_id(selected))

    # LEVEL 4: Snack supplement-style fallback proxy (prefer high-protein low-cal recipe).
    if assigned_slots.get("snack") is None:
        fallback_level_reached = max(fallback_level_reached, 4)
        snack_candidates = [
            recipe for recipe in recipes
            if _get_stable_recipe_id(recipe) not in used_recipe_ids
        ]
        if snack_candidates:
            snack_candidates.sort(
                key=lambda recipe: (
                    -(_safe_float(recipe.get("Protein", 0)) / max(_safe_float(recipe.get("Calories", 0)), 1.0)),
                    abs(_safe_float(recipe.get("Calories", 0)) - _safe_float(slot_targets.get("snack", {}).get("calories", 0))),
                    _get_recipe_name_key(recipe),
                )
            )
            assigned_slots["snack"] = snack_candidates[0]
            used_recipe_ids.add(_get_stable_recipe_id(snack_candidates[0]))

    # LEVEL 5: Global best match (ignore diversity constraints).
    if not is_plan_valid(assigned_slots):
        fallback_level_reached = max(fallback_level_reached, 5)
        for slot in MEAL_SLOTS:
            if assigned_slots.get(slot) is not None:
                continue

            global_candidates = [
                recipe for recipe in recipes
                if _get_stable_recipe_id(recipe) not in used_recipe_ids
            ]
            if not global_candidates:
                global_candidates = list(recipes)

            global_candidates.sort(
                key=lambda recipe: (
                    calculate_weighted_slot_error(recipe, slot_targets.get(slot, {})),
                    _get_recipe_name_key(recipe),
                )
            )
            chosen = global_candidates[0]
            assigned_slots[slot] = chosen
            used_recipe_ids.add(_get_stable_recipe_id(chosen))

    meta = {
        "fallback_level": fallback_level_reached,
        "history_applied": bool(meal_history),
    }
    return assigned_slots, used_recipe_ids, meta


def _build_ranked_bucket_candidates(
    recipes: List[Dict[str, Any]],
    slot: str,
    slot_targets: Dict[str, Dict[str, float]],
) -> List[Tuple[float, Dict[str, Any]]]:
    """Build deterministic ranked candidates for one slot from bucket constraints."""
    slot_target = slot_targets.get(slot, {})
    ranked: List[Tuple[float, Dict[str, Any]]] = []

    for recipe in recipes:
        if not _check_slot_thresholds(recipe, slot_target, slot, tolerance_multiplier=1.0):
            continue
        ranked.append((calculate_weighted_slot_error(recipe, slot_target), recipe))

    ranked.sort(key=lambda item: (item[0], _get_recipe_name_key(item[1]), _get_stable_recipe_id(item[1])))
    return ranked


def _recent_penalty(
    recipe_name: str,
    slot_history: List[str],
    bucket_size: int,
) -> float:
    """Apply spec diversity penalties with easing for small buckets."""
    if not recipe_name:
        return 0.0

    penalty = 0.0
    if slot_history and slot_history[0] == recipe_name:
        penalty = LAST_24H_REPEAT_PENALTY
    elif recipe_name in slot_history[1:3]:
        penalty = RECENT_REPEAT_PENALTY

    # Small dataset mode: allow reuse after 2-3 days by reducing pressure.
    if bucket_size <= 3 and penalty == RECENT_REPEAT_PENALTY:
        return 0.0
    if bucket_size <= 6:
        penalty *= 0.7

    return round(penalty, 6)


def apply_diversity_aware_final_selection(
    assigned_slots: Dict[str, Optional[Dict[str, Any]]],
    recipes: List[Dict[str, Any]],
    slot_targets: Dict[str, Dict[str, float]],
    meal_history: Optional[Dict[str, List[str]]] = None,
    selection_seed: str = "",
) -> Tuple[Dict[str, Optional[Dict[str, Any]]], Dict[str, Any]]:
    """Run diversity-aware random top-3 selection after bucket generation.

    This layer must run only after bucket generation/redistribution has produced a valid
    baseline assignment. Nutrition fit remains primary via weighted error ordering.
    """
    if not assigned_slots:
        return assigned_slots, {"applied": False, "reason": "empty_assignment"}

    history = _normalize_meal_history(meal_history)
    selected_slots: Dict[str, Optional[Dict[str, Any]]] = dict(assigned_slots)
    used_ids: Set[str] = {
        _get_stable_recipe_id(recipe)
        for recipe in selected_slots.values()
        if recipe is not None
    }

    slot_candidate_map: Dict[str, List[Tuple[float, float, Dict[str, Any], bool]]] = {}
    all_repeated_fallback_slots: List[str] = []

    # First pass: per-slot top-3 random pick using final_score = error + diversity_penalty.
    for slot in MEAL_SLOTS:
        ranked = _build_ranked_bucket_candidates(recipes, slot, slot_targets)
        if not ranked:
            continue

        current_recipe = selected_slots.get(slot)
        current_id = _get_stable_recipe_id(current_recipe) if current_recipe is not None else ""
        if current_id:
            used_ids.discard(current_id)

        slot_history = history.get(slot, [])
        scored: List[Tuple[float, float, Dict[str, Any], bool]] = []
        non_repeated: List[Tuple[float, float, Dict[str, Any], bool]] = []

        for error_score, recipe in ranked:
            name_key = _get_recipe_name_key(recipe)
            is_recent_repeat = name_key in slot_history[:3]
            penalty = _recent_penalty(name_key, slot_history, len(ranked))
            final_score = round(error_score + penalty, 6)
            row = (final_score, error_score, recipe, is_recent_repeat)
            scored.append(row)
            if not is_recent_repeat:
                non_repeated.append(row)

        # Repeat control primary rule: avoid recent repeats where possible.
        working = non_repeated if non_repeated else scored
        if not non_repeated:
            all_repeated_fallback_slots.append(slot)

        working.sort(key=lambda item: (item[0], _get_recipe_name_key(item[2]), _get_stable_recipe_id(item[2])))
        slot_candidate_map[slot] = working

        top_k = working[: min(3, len(working))]
        if not top_k:
            continue

        rng_seed = f"{selection_seed}|{slot}|{len(top_k)}"
        rng = random.Random(rng_seed)
        ordered_indices = list(range(len(top_k)))
        rng.shuffle(ordered_indices)

        chosen_recipe: Optional[Dict[str, Any]] = None
        for idx in ordered_indices:
            candidate_recipe = top_k[idx][2]
            cid = _get_stable_recipe_id(candidate_recipe)
            if cid in used_ids:
                continue
            chosen_recipe = candidate_recipe
            used_ids.add(cid)
            break

        if chosen_recipe is None:
            # Edge-case fallback: ignore diversity and pick lowest nutrition error.
            for _, error_score, candidate_recipe, _ in sorted(working, key=lambda item: (item[1], item[0])):
                cid = _get_stable_recipe_id(candidate_recipe)
                if cid in used_ids:
                    continue
                chosen_recipe = candidate_recipe
                used_ids.add(cid)
                break

        if chosen_recipe is not None:
            selected_slots[slot] = chosen_recipe
        elif current_recipe is not None:
            selected_slots[slot] = current_recipe

        final_recipe = selected_slots.get(slot)
        if final_recipe is not None:
            used_ids.add(_get_stable_recipe_id(final_recipe))

    # Global repeat control: allow partial reuse but ensure at least 50% new meals.
    def _count_recent_repeats(plan_slots: Dict[str, Optional[Dict[str, Any]]]) -> int:
        repeats = 0
        for slot in MEAL_SLOTS:
            recipe = plan_slots.get(slot)
            if recipe is None:
                continue
            if _get_recipe_name_key(recipe) in history.get(slot, [])[:3]:
                repeats += 1
        return repeats

    repeat_count = _count_recent_repeats(selected_slots)
    min_new_meals = 2

    if repeat_count > 2 or (len(MEAL_SLOTS) - repeat_count) < min_new_meals:
        for slot in MEAL_SLOTS:
            current_recipe = selected_slots.get(slot)
            if current_recipe is None:
                continue
            current_name = _get_recipe_name_key(current_recipe)
            if current_name not in history.get(slot, [])[:3]:
                continue

            alternatives = [
                item for item in slot_candidate_map.get(slot, [])
                if not item[3]
            ]
            alternatives.sort(key=lambda item: (item[0], item[1]))

            for _, _, alt_recipe, _ in alternatives:
                alt_id = _get_stable_recipe_id(alt_recipe)
                current_id = _get_stable_recipe_id(current_recipe)
                if alt_id in used_ids and alt_id != current_id:
                    continue

                selected_slots[slot] = alt_recipe
                if alt_id != current_id:
                    used_ids.discard(current_id)
                    used_ids.add(alt_id)
                break

            repeat_count = _count_recent_repeats(selected_slots)
            if repeat_count <= 2 and (len(MEAL_SLOTS) - repeat_count) >= min_new_meals:
                break

    # Guarantee output by preserving already-assigned slot recipes.
    for slot in MEAL_SLOTS:
        if selected_slots.get(slot) is None and assigned_slots.get(slot) is not None:
            selected_slots[slot] = assigned_slots[slot]

    meta = {
        "applied": True,
        "repeat_count": _count_recent_repeats(selected_slots),
        "new_meal_count": len(MEAL_SLOTS) - _count_recent_repeats(selected_slots),
        "all_repeated_fallback_slots": all_repeated_fallback_slots,
    }
    return selected_slots, meta


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
        >>> macros = {"protein": 200, "carbohydrates": 150, "fat": 70}
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


def calculate_weighted_slot_error(
    recipe: Dict[str, Any],
    slot_target: Dict[str, float],
) -> float:
    """Compute weighted fit error between a recipe and one meal slot target."""
    calorie_error = calculate_macro_error(
        _safe_float(recipe.get("Calories", 0)),
        _safe_float(slot_target.get("calories", 0)),
    )
    protein_error = calculate_macro_error(
        _safe_float(recipe.get("Protein", 0)),
        _safe_float(slot_target.get("protein", 0)),
    )
    carb_error = calculate_macro_error(
        _safe_float(recipe.get("Carbohydrates", recipe.get("Carbs", 0))),
        _safe_float(slot_target.get("carbohydrates", 0)),
    )
    fat_error = calculate_macro_error(
        _safe_float(recipe.get("Fat", 0)),
        _safe_float(slot_target.get("fat", 0)),
    )

    return (
        (calorie_error * CALORIE_ERROR_WEIGHT)
        + (protein_error * PROTEIN_ERROR_WEIGHT)
        + (carb_error * CARB_ERROR_WEIGHT)
        + (fat_error * FAT_ERROR_WEIGHT)
    )


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


def _check_slot_thresholds(
    recipe: Dict[str, Any],
    slot_target: Dict[str, float],
    slot_name: str,
    tolerance_multiplier: float = 1.0,
) -> bool:
    """Check slot thresholds with optional deterministic tolerance expansion."""
    recipe_calories = _safe_float(recipe.get("Calories", 0))
    recipe_protein = _safe_float(recipe.get("Protein", 0))
    target_calories = _safe_float(slot_target.get("calories", 0))
    target_protein = _safe_float(slot_target.get("protein", 0))

    if target_calories <= 0:
        return False

    calorie_tolerance = (
        BREAKFAST_CALORIE_TOLERANCE if slot_name == "breakfast" else OTHER_MEAL_CALORIE_TOLERANCE
    ) * max(tolerance_multiplier, 1.0)
    protein_tolerance = PROTEIN_TOLERANCE * max(tolerance_multiplier, 1.0)

    calorie_ok = (
        target_calories * (1 - calorie_tolerance)
        <= recipe_calories
        <= target_calories * (1 + calorie_tolerance)
    )

    if target_protein <= 0:
        protein_ok = recipe_protein <= 5
    else:
        protein_ok = (
            target_protein * (1 - protein_tolerance)
            <= recipe_protein
            <= target_protein * (1 + protein_tolerance)
        )

    return calorie_ok and protein_ok


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
    3. Prevent duplicate recipe usage (by stable recipe id)
      4. Return slot name or None if no valid assignment

    Args:
        recipe: Recipe dict with Calories, Protein, Carbohydrates, Fat
        slot_targets: Dict mapping slot name to target macros
        assigned_slots: Dict mapping slot name to assigned recipe (or None)
        used_recipes: Set of stable recipe ids already used

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

    stable_id = _get_stable_recipe_id(recipe)
    if stable_id in used_recipes:
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


def optimize_bucket_assignment(
    recipes: List[Dict[str, Any]],
    slot_targets: Dict[str, Dict[str, float]],
    tolerance_multiplier: float = 1.0,
) -> Tuple[Dict[str, Optional[Dict[str, Any]]], Set[str], float]:
    """Globally optimize one recipe per slot using deterministic weighted error.

    Returns:
        (assigned_slots, used_recipe_ids, total_error)
    """
    assigned_slots: Dict[str, Optional[Dict[str, Any]]] = {slot: None for slot in MEAL_SLOTS}
    if not recipes:
        return assigned_slots, set(), float("inf")

    slot_candidates: Dict[str, List[Tuple[float, Dict[str, Any]]]] = {slot: [] for slot in MEAL_SLOTS}

    for recipe in recipes:
        for slot in MEAL_SLOTS:
            slot_target = slot_targets.get(slot, {})
            if not _check_slot_thresholds(recipe, slot_target, slot, tolerance_multiplier=tolerance_multiplier):
                continue
            error = calculate_weighted_slot_error(recipe, slot_target)
            slot_candidates[slot].append((error, recipe))

    for slot in MEAL_SLOTS:
        slot_candidates[slot].sort(key=lambda item: (item[0], item[1].get("RecipeName", "")))
        if len(slot_candidates[slot]) > MAX_CANDIDATES_PER_SLOT:
            slot_candidates[slot] = slot_candidates[slot][:MAX_CANDIDATES_PER_SLOT]

    ordered_slots = sorted(MEAL_SLOTS, key=lambda slot: len(slot_candidates[slot]))
    if any(len(slot_candidates[slot]) == 0 for slot in ordered_slots):
        return assigned_slots, set(), float("inf")

    best_total_error = float("inf")
    best_assignment: Dict[str, Optional[Dict[str, Any]]] = {slot: None for slot in MEAL_SLOTS}

    def dfs(slot_idx: int, running_error: float, used_ids: Set[str], current_assignment: Dict[str, Optional[Dict[str, Any]]]) -> None:
        nonlocal best_total_error, best_assignment

        if running_error >= best_total_error:
            return

        if slot_idx >= len(ordered_slots):
            best_total_error = running_error
            best_assignment = dict(current_assignment)
            return

        slot_name = ordered_slots[slot_idx]
        for error, recipe in slot_candidates[slot_name]:
            stable_id = _get_stable_recipe_id(recipe)
            if stable_id in used_ids:
                continue

            current_assignment[slot_name] = recipe
            used_ids.add(stable_id)
            dfs(slot_idx + 1, running_error + error, used_ids, current_assignment)
            used_ids.remove(stable_id)
            current_assignment[slot_name] = None

    dfs(0, 0.0, set(), {slot: None for slot in MEAL_SLOTS})

    used_recipe_ids = {
        _get_stable_recipe_id(recipe)
        for recipe in best_assignment.values()
        if recipe is not None
    }
    return best_assignment, used_recipe_ids, best_total_error


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
        >>> get_redistribution_target(["breakfast"], ["lunch", "dinner", "snack"])
        "snack"  # Snack has smallest calorie requirement and is filled
    """
    if "snack" in filled_slots and len(empty_slots) > 0:
        return "snack"  # Snack has 10% requirement, easiest to reallocate
    # In other cases, recommend keeping current assignment
    return None


def redistribute_empty_slots(
    assigned_slots: Dict[str, Optional[Dict[str, Any]]],
    all_recipes: List[Dict[str, Any]],
    slot_targets: Dict[str, Dict[str, float]],
    used_recipe_ids: Set[str],
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Fill empty slots with deterministic redistribution and relaxed matching.

    Note: this function does not mutate the incoming used_recipe_ids set.
    """
    rebalanced = dict(assigned_slots)
    used_recipe_ids_local = set(used_recipe_ids)
    remaining_recipes = [r for r in all_recipes if _get_stable_recipe_id(r) not in used_recipe_ids_local]

    # Progressive relaxation keeps behavior deterministic and bounded.
    tolerance_levels = (1.0, 1.25, 1.5, 1.75, 2.0)

    for slot in MEAL_SLOTS:
        if rebalanced.get(slot) is not None:
            continue

        slot_target = slot_targets.get(slot, {})
        best_recipe = None
        best_error = float("inf")

        for multiplier in tolerance_levels:
            for recipe in remaining_recipes:
                if not _check_slot_thresholds(recipe, slot_target, slot, tolerance_multiplier=multiplier):
                    continue
                err = calculate_weighted_slot_error(recipe, slot_target)
                if err < best_error:
                    best_error = err
                    best_recipe = recipe

            if best_recipe is not None:
                break

        if best_recipe is not None:
            rebalanced[slot] = best_recipe
            rid = _get_stable_recipe_id(best_recipe)
            used_recipe_ids_local.add(rid)
            remaining_recipes = [r for r in remaining_recipes if _get_stable_recipe_id(r) != rid]

    return rebalanced


def improve_assignment_with_single_slot_swaps(
    assigned_slots: Dict[str, Optional[Dict[str, Any]]],
    all_recipes: List[Dict[str, Any]],
    slot_targets: Dict[str, Dict[str, float]],
    tolerance_multiplier: float = 1.25,
    max_iterations: int = MAX_SWAP_OPTIMIZATION_ITERATIONS,
) -> Tuple[Dict[str, Optional[Dict[str, Any]]], bool]:
    """Improve a full assignment by deterministic single-slot swap local search.

    Optimization target (lexicographic):
      1) absolute daily calorie gap to slot target sum
      2) summed weighted slot error

    Returns:
      (improved_assignment, changed)
    """
    working = dict(assigned_slots)
    if not is_plan_valid(working):
        return working, False

    target_daily_calories = sum(_safe_float(slot_targets.get(slot, {}).get("calories", 0)) for slot in MEAL_SLOTS)

    def score_plan(plan: Dict[str, Optional[Dict[str, Any]]]) -> Tuple[float, float]:
        total_calories = 0.0
        total_error = 0.0
        for slot in MEAL_SLOTS:
            recipe = plan.get(slot)
            if recipe is None:
                continue
            total_calories += _safe_float(recipe.get("Calories", 0))
            total_error += calculate_weighted_slot_error(recipe, slot_targets.get(slot, {}))

        calorie_gap = abs(total_calories - target_daily_calories)
        return (round(calorie_gap, 6), round(total_error, 6))

    changed = False
    current_score = score_plan(working)

    for _ in range(max(0, max_iterations)):
        used_ids = {_get_stable_recipe_id(recipe) for recipe in working.values() if recipe is not None}
        best_move = None
        best_move_score = current_score
        best_tie_breaker: Tuple[str, str] = ("~", "~")

        for slot in MEAL_SLOTS:
            current_recipe = working.get(slot)
            if current_recipe is None:
                continue

            current_recipe_id = _get_stable_recipe_id(current_recipe)
            slot_target = slot_targets.get(slot, {})

            slot_candidates: List[Tuple[float, Dict[str, Any]]] = []
            for recipe in all_recipes:
                rid = _get_stable_recipe_id(recipe)
                if rid in used_ids and rid != current_recipe_id:
                    continue
                if not _check_slot_thresholds(recipe, slot_target, slot, tolerance_multiplier=tolerance_multiplier):
                    continue
                slot_candidates.append((calculate_weighted_slot_error(recipe, slot_target), recipe))

            slot_candidates.sort(key=lambda item: (item[0], item[1].get("RecipeName", "")))
            if len(slot_candidates) > MAX_CANDIDATES_PER_SLOT:
                slot_candidates = slot_candidates[:MAX_CANDIDATES_PER_SLOT]

            for _, candidate in slot_candidates:
                if candidate is current_recipe:
                    continue

                tentative = dict(working)
                tentative[slot] = candidate
                tentative_score = score_plan(tentative)
                tie_breaker = (slot, str(candidate.get("RecipeName", "")))

                if (tentative_score, tie_breaker) < (best_move_score, best_tie_breaker):
                    best_move_score = tentative_score
                    best_move = (slot, candidate)
                    best_tie_breaker = tie_breaker

        if best_move is None or best_move_score >= current_score:
            break

        slot_name, candidate_recipe = best_move
        working[slot_name] = candidate_recipe
        current_score = best_move_score
        changed = True

    return working, changed


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

    # Defensively compute average slot calories
    total_slot_calories = sum(
        slot_targets.get(s, {}).get("calories", 0) if isinstance(slot_targets.get(s), dict) else 0
        for s in MEAL_SLOTS
    )
    avg_slot_calories = total_slot_calories / max(1, len(MEAL_SLOTS))
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
