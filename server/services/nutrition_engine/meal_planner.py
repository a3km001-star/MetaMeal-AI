"""Main service layer for the nutrition-engine meal planner (SPEC-COMPLIANT).

This module implements a deterministic 14-step constraint workflow:

1. Metabolic Base
2. Carb Baseline Subtraction
3. Diet Filtering
4. Allergy Filtering
5. Age-Based Scaling
6. Meal Split (25/35/30/10)
7. Error-Based Matching
8. Bucket Assignment
9. Validity Check
10. Fallback (multiply_factor=2.5)
11. Redistribution
12. Supplement Solver
13. Final Validation
14. Output Formatting
"""

import logging
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timezone, date, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import time

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from services.nutrition_engine.constraint_solver import (
    filter_by_allergies,
    filter_by_diet,
)
from services.nutrition_engine.macro_split import MacroSplit, calculate_macros
from services.nutrition_engine.metabolic_calculator import (
    ActivityLevel,
    FitnessGoal,
    Sex,
    calculate_bmr,
    calculate_tdee,
)
from services.nutrition_engine.spec_compliant_steps import (
    MEAL_SLOTS,
    apply_diversity_aware_final_selection,
    apply_carb_baseline,
    get_age_multiply_factor,
    improve_assignment_with_single_slot_swaps,
    is_plan_valid,
    optimize_bucket_assignment,
    redistribute_empty_slots,
    scale_recipe_by_factor,
    split_calories_by_meal_slot,
    split_macros_by_meal_slot,
)
from utils.helpers import load_food_dataset

logger = logging.getLogger(__name__)

GOAL_ADJUSTMENTS: Dict[FitnessGoal, float] = {
    FitnessGoal.FAT_LOSS: -0.20,
    FitnessGoal.MUSCLE_GAIN: 0.15,
    FitnessGoal.MAINTENANCE: 0.0,
}
MIN_CALORIES_BY_SEX: Dict[Sex, int] = {
    Sex.MALE: 1500,
    Sex.FEMALE: 1200,
}
MAX_REGENERATION_ATTEMPTS = 5
HISTORY_DB_READ_TIMEOUT_SECONDS = 0.35
HISTORY_DB_WRITE_TIMEOUT_SECONDS = 0.20
HISTORY_DB_COOLDOWN_SECONDS = 300

_history_db_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="meal-history-db")
_history_db_disabled_until: Optional[datetime] = None


def _history_db_is_disabled(now_utc: Optional[datetime] = None) -> bool:
    """Return True while circuit breaker cooldown is active."""
    if _history_db_disabled_until is None:
        return False

    now = now_utc or datetime.now(timezone.utc)
    return now < _history_db_disabled_until


def _disable_history_db_temporarily(reason: str) -> None:
    """Open circuit breaker to prevent repeated blocking DB attempts."""
    global _history_db_disabled_until
    _history_db_disabled_until = datetime.now(timezone.utc) + timedelta(seconds=HISTORY_DB_COOLDOWN_SECONDS)
    logger.warning("Meal history DB temporarily disabled for %ss: %s", HISTORY_DB_COOLDOWN_SECONDS, reason)


def _run_history_db_call_with_timeout(callable_obj: Any, timeout_seconds: float) -> Any:
    """Execute DB call with a strict timeout to protect API latency."""
    future = _history_db_executor.submit(callable_obj)
    try:
        return future.result(timeout=timeout_seconds)
    except TimeoutError:
        future.cancel()
        raise


def _profile_history_key(user_profile: "UserProfile") -> str:
    """Build a stable profile key for meal-history grouping."""
    payload = {
        "age": user_profile.age,
        "weight": round(_coerce_float(user_profile.weight, 0.0), 2),
        "height": round(_coerce_float(user_profile.height, 0.0), 2),
        "sex": user_profile.sex.value,
        "activity_level": user_profile.activity_level.value,
        "goal": user_profile.goal.value,
        "diet_type": (user_profile.diet_type or "").strip().lower(),
        "allergies": sorted((user_profile.allergies or [])),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def _recipe_name_from_record(value: Any) -> str:
    return str(value or "").strip().lower()


def _load_recent_meal_history(user_profile: "UserProfile", lookback_days: int = 3) -> Dict[str, List[str]]:
    """Load recent meal names by slot from DB and merge caller-provided last_meals."""
    merged_history: Dict[str, List[str]] = {slot: [] for slot in MEAL_SLOTS}
    provided = user_profile.last_meals or {}

    for slot in MEAL_SLOTS:
        incoming = provided.get(slot, []) if isinstance(provided, dict) else []
        if isinstance(incoming, list):
            merged_history[slot] = [_recipe_name_from_record(item) for item in incoming if _recipe_name_from_record(item)]

    if _history_db_is_disabled():
        return merged_history

    try:
        from db.mongo import meal_plans_collection

        today = datetime.now(timezone.utc).date()
        profile_key = _profile_history_key(user_profile)

        def _read_docs() -> List[Dict[str, Any]]:
            return list(
                meal_plans_collection.find({"profile_key": profile_key})
                .sort("date", -1)
                .limit(10)
            )

        docs = _run_history_db_call_with_timeout(_read_docs, HISTORY_DB_READ_TIMEOUT_SECONDS)

        for doc in docs:
            raw_date = str(doc.get("date") or "").strip()
            if not raw_date:
                continue
            try:
                plan_date = date.fromisoformat(raw_date)
            except ValueError:
                continue

            day_delta = (today - plan_date).days
            # Include same-day generated plans so repeated requests can diversify.
            if day_delta < 0 or day_delta > lookback_days:
                continue

            meals = doc.get("meals", {})
            if not isinstance(meals, dict):
                continue

            for slot in MEAL_SLOTS:
                meal_name = _recipe_name_from_record(meals.get(slot))
                if not meal_name:
                    continue
                if meal_name not in merged_history[slot]:
                    merged_history[slot].append(meal_name)
    except TimeoutError:
        _disable_history_db_temporarily("history read timeout")
    except Exception as exc:
        _disable_history_db_temporarily(f"history read error: {exc}")

    return merged_history


def _extract_slot_meal_names_from_plan(plan: "CompleteMealPlan") -> Dict[str, str]:
    """Extract slot -> recipe name from formatted plan or fallback meal labels."""
    names: Dict[str, str] = {slot: "" for slot in MEAL_SLOTS}

    if isinstance(plan.meal_plan, dict) and plan.meal_plan:
        for slot in MEAL_SLOTS:
            slot_entry = plan.meal_plan.get(slot)
            if isinstance(slot_entry, dict):
                names[slot] = str(slot_entry.get("name") or "").strip()

    for meal in plan.meals:
        meal_name = str(meal.name or "")
        if " - " not in meal_name:
            continue
        slot, recipe_name = meal_name.split(" - ", 1)
        slot = slot.strip().lower()
        if slot in names and not names[slot]:
            names[slot] = recipe_name.strip()

    return {slot: value for slot, value in names.items() if value}


def _persist_generated_meal_history(user_profile: "UserProfile", plan: "CompleteMealPlan") -> None:
    """Persist generated meal names so future days can penalize repeats."""
    if _history_db_is_disabled():
        return

    try:
        from db.mongo import meal_plans_collection

        today_str = datetime.now(timezone.utc).date().isoformat()
        meals = _extract_slot_meal_names_from_plan(plan)
        if len(meals) != len(MEAL_SLOTS):
            return

        payload = {
            "date": today_str,
            "meals": meals,
            "profile_key": _profile_history_key(user_profile),
            "created_at": datetime.now(timezone.utc),
        }

        def _write_doc() -> Any:
            return meal_plans_collection.insert_one(payload)

        _run_history_db_call_with_timeout(_write_doc, HISTORY_DB_WRITE_TIMEOUT_SECONDS)
    except TimeoutError:
        _disable_history_db_temporarily("history write timeout")
    except Exception as exc:
        _disable_history_db_temporarily(f"history write error: {exc}")


def _coerce_float(value: Any, default: float = 0.0) -> float:
    """Safely convert incoming values to float."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_reasonable_nutrition_row(normalized: Dict[str, Any]) -> bool:
    """Return False for obviously invalid/outlier macro rows."""
    calories = _coerce_float(normalized.get("Calories", 0))
    protein = _coerce_float(normalized.get("Protein", 0))
    carbs = _coerce_float(normalized.get("Carbohydrates", 0))
    fat = _coerce_float(normalized.get("Fat", 0))

    if calories <= 0 or protein < 0 or carbs < 0 or fat < 0:
        return False

    macro_kcal = (4 * protein) + (4 * carbs) + (9 * fat)
    kcal_ratio = macro_kcal / max(calories, 1e-6)

    if kcal_ratio < 0.35 or kcal_ratio > 4.0:
        return False
    if protein > 150 or carbs > 250 or fat > 150:
        return False

    return True


def _normalize_food_for_multiply_factor(food: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize dataset row into spec-compliant format."""
    calories = _coerce_float(food.get("Calories", food.get("Calories (kcal)", 0)))
    protein = _coerce_float(food.get("Protein", food.get("Protein(g)", 0)))
    carbs = _coerce_float(food.get("Carbohydrates", food.get("Carbohydrates (g)", 0)))
    fat = _coerce_float(food.get("Fat", food.get("Fat (g)", 0)))

    normalized: Dict[str, Any] = {
        "RecipeName": food.get("RecipeName", "Unknown Meal"),
        "DisplayName": food.get("RecipeName", "Unknown Meal"),
        "Ingredients": food.get("Ingredients") or food.get("Cleaned-Ingredients") or "",
        "Instructions": food.get("Instructions") or food.get("TranslatedInstructions") or "",
        "DietType": food.get("DietType") or food.get("vegornonveg") or "Unknown",
        "Calories": calories,
        "Protein": protein,
        "Carbohydrates": carbs,
        "Fat": fat,
    }

    return normalized if _is_reasonable_nutrition_row(normalized) else None


def _prepare_foods_for_profile_spec_compliant(
    foods: List[Any],
    user_profile: "UserProfile",
) -> List[Dict[str, Any]]:
    """Prepare and scale foods using age-based multiply_factor (SPEC STEP 4)."""
    multiply_factor = get_age_multiply_factor(user_profile.age)
    normalized_foods: List[Dict[str, Any]] = []

    for row in foods:
        # Handle both direct dicts and nested lists
        rows_to_process = [row] if isinstance(row, dict) else (row if isinstance(row, list) else [])

        for item in rows_to_process:
            if not isinstance(item, dict):
                continue

            normalized = _normalize_food_for_multiply_factor(item)
            if not normalized or not normalized["RecipeName"].strip():
                continue

            # Scale by multiply_factor
            scaled = scale_recipe_by_factor(normalized, multiply_factor)
            normalized_foods.append(scaled)

    return normalized_foods


class UserProfile(BaseModel):
    """Validated user profile for meal-plan generation."""

    age: int = Field(..., ge=15, le=100, description="Age in years")
    weight: float = Field(..., ge=30, le=300, description="Weight in kilograms")
    height: float = Field(..., ge=100, le=250, description="Height in centimeters")
    sex: Sex = Field(..., description="Biological sex")
    activity_level: ActivityLevel = Field(..., description="Activity level")
    goal: FitnessGoal = Field(..., description="Fitness goal")
    diet_type: Optional[str] = Field(None, description="Diet preference")
    allergies: Optional[List[str]] = Field(default_factory=list, description="Allergens to avoid")
    last_meals: Optional[Dict[str, List[str]]] = Field(default_factory=dict, description="Recent meals by slot")

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, value: float) -> float:
        if value < 30 or value > 300:
            raise ValueError("Weight must be between 30 and 300 kg")
        return value

    @field_validator("height")
    @classmethod
    def validate_height(cls, value: float) -> float:
        if value < 100 or value > 250:
            raise ValueError("Height must be between 100 and 250 cm")
        return value


# ============================================================================
# DATA MODELS
# ============================================================================


class MealItem(BaseModel):
    """Internal normalized meal object."""

    name: str
    calories: float
    protein: float
    carbohydrates: float
    fat: float
    ingredients: str
    instructions: str
    diet_type: str


class SupplementItem(BaseModel):
    """Normalized supplement item."""

    name: str
    calories: float
    protein: float
    carbohydrates: float
    fat: float
    ingredients: str
    instructions: str
    diet_type: str


class CompleteMealPlan(BaseModel):
    """Complete meal plan with validation and formatting."""

    user_profile: Dict[str, Any]
    bmr: float
    tdee: float
    calorie_target: float
    macros: Dict[str, float]
    macro_percentages: Dict[str, float]
    meals: List[MealItem]
    supplements: List[SupplementItem] = Field(default_factory=list)
    meal_plan: Optional[Dict[str, Dict[str, Any]]] = None
    meal_count: int
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    calorie_accuracy: float
    goal: str
    activity_level: str
    solver_mode: str = "strict"
    fallback_reason: Optional[str] = None
    attempt_count: int = 1
    warnings: List[str] = Field(default_factory=list)

    def to_frontend_response(self) -> Dict[str, Any]:
        """Return frontend-ready JSON response."""
        response = {
            "calorie_target": self.calorie_target,
            "macros": {
                "protein": self.macros["protein"],
                "carbs": self.macros["carbohydrates"],
                "fat": self.macros["fat"],
            },
            "meal_plan": self.meal_plan or {},
            "supplements": [
                {
                    "name": s.name,
                    "protein": s.protein,
                    "calories": s.calories,
                }
                for s in self.supplements
            ],
            "solver": {
                "mode": self.solver_mode,
                "attempt_count": self.attempt_count,
                "fallback_reason": self.fallback_reason,
            },
        }
        if self.warnings:
            response["warnings"] = self.warnings
        return response


# ============================================================================
# SPEC-COMPLIANT ALGORITHM IMPLEMENTATION
# ============================================================================


def _adjust_calories_for_goal(tdee: float, goal: FitnessGoal, sex: Sex) -> float:
    """SPEC STEP 1: Adjust TDEE for fitness goal."""
    if tdee <= 0:
        raise HTTPException(status_code=400, detail="TDEE must be positive")

    adjustment = GOAL_ADJUSTMENTS.get(goal)
    if adjustment is None:
        raise HTTPException(status_code=400, detail=f"Unsupported goal: {goal}")

    calorie_target = tdee * (1 + adjustment)
    calorie_target = max(calorie_target, MIN_CALORIES_BY_SEX.get(sex, 1200))
    return round(calorie_target, 2)


def _generate_validated_meal_plan_spec_compliant(
    user_profile: UserProfile,
    foods: List[Dict[str, Any]],
) -> CompleteMealPlan:
    """Generate meal plan using deterministic 14-step constraint pipeline."""
    from services.nutrition_engine.meal_formatter import format_meal_plan
    from services.nutrition_engine.meal_validator import validate_meal_plan as validate_generated_plan
    from services.nutrition_engine.supplement_solver import fill_macro_gap, load_supplements

    if not foods:
        raise HTTPException(status_code=500, detail="Dataset is empty")

    # STEP 1: Metabolic Base
    logger.info("STEP 1: Calculating metabolic base")
    bmr = calculate_bmr(user_profile.age, user_profile.weight, user_profile.height, user_profile.sex)
    tdee = calculate_tdee(bmr, user_profile.activity_level)
    calorie_target = _adjust_calories_for_goal(tdee, user_profile.goal, user_profile.sex)
    logger.info(f"BMR={bmr}, TDEE={tdee}, Target={calorie_target}")

    # STEP 2: Carb Baseline Adjustment
    logger.info("STEP 2: Applying carb baseline adjustment")
    adjusted_calories = apply_carb_baseline(calorie_target)
    logger.info(f"Adjusted calories: {calorie_target} - 390 = {adjusted_calories}")

    # Recalculate macros from adjusted calories
    macros = calculate_macros(
        calories=adjusted_calories,
        goal=user_profile.goal,
        weight_kg=user_profile.weight,
    )
    logger.info(f"Macros: P={macros.protein_grams}g, C={macros.carb_grams}g, F={macros.fat_grams}g")

    # STEP 3 + STEP 4: Diet and allergy filtering
    logger.info("STEP 3/4: Filtering by diet and allergies")
    prepared_foods = _prepare_foods_for_profile_spec_compliant(foods, user_profile)
    global_warnings: List[str] = []

    diet_filtered_foods = filter_by_diet(prepared_foods, user_profile.diet_type)
    filtered_foods = filter_by_allergies(diet_filtered_foods, user_profile.allergies or [])
    logger.info(f"After filtering: {len(filtered_foods)} foods available")

    if not filtered_foods:
        # Deterministic over-filter fallback chain: keep output generation alive.
        if diet_filtered_foods:
            filtered_foods = list(diet_filtered_foods)
            global_warnings.append(
                "Allergy filtering removed all recipes; proceeding with diet-only foods."
            )
        elif prepared_foods:
            filtered_foods = list(prepared_foods)
            global_warnings.append(
                "Diet and allergy filtering removed all recipes; using minimally filtered foods."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="No foods available after dataset normalization",
            )

    supplements_dataset = load_supplements()
    recent_meal_history = _load_recent_meal_history(user_profile)
    history_seed = (
        f"{_profile_history_key(user_profile)}"
        f"|{datetime.now(timezone.utc).date().isoformat()}"
        f"|req:{time.time_ns()}"
    )
    best_candidate_plan: Optional[CompleteMealPlan] = None
    last_error = "Validation failed"
    best_candidate_score = float("inf")

    # Retry loop with fallback strategies
    for attempt in range(1, MAX_REGENERATION_ATTEMPTS + 1):
        try:
            logger.info(f"ATTEMPT {attempt}/{MAX_REGENERATION_ATTEMPTS}")

            # STEP 5 + STEP 10: Age-based scaling with fallback multiplier on late attempts.
            if attempt >= 4:
                logger.info("STEP 10: Using fallback multiply_factor=2.5")
                multiply_factor = 2.5
                age_factor = get_age_multiply_factor(user_profile.age)
                if not age_factor or age_factor <= 0:
                    logger.warning(f"Invalid age_factor {age_factor} for age {user_profile.age}, using 1.6 as fallback")
                    age_factor = 1.6
                scaled_foods = [scale_recipe_by_factor(f, multiply_factor / age_factor) for f in filtered_foods]
            else:
                scaled_foods = list(filtered_foods)

            # STEP 6: Meal split
            logger.info("STEP 6: Calculating meal slot targets")
            slot_calorie_targets = split_calories_by_meal_slot(adjusted_calories)
            slot_macro_targets = split_macros_by_meal_slot(slot_calorie_targets, {
                "protein": macros.protein_grams,
                "carbohydrates": macros.carb_grams,
                "fat": macros.fat_grams,
            })
            logger.info(f"Slot targets: {slot_calorie_targets}")

            # STEP 7 + STEP 8: Bucket assignment (kept deterministic and nutrition-first).
            logger.info("STEP 7/8: Running nutrition-first bucket assignment")
            assigned_slots, used_recipes, bucket_error = optimize_bucket_assignment(
                scaled_foods,
                slot_macro_targets,
                tolerance_multiplier=1.0,
            )
            logger.info(f"Bucket assignment error: {bucket_error}")

            # STEP 9: Initial validity check.
            logger.info("STEP 9: Checking initial slot validity")
            initial_valid = is_plan_valid(assigned_slots)

            # STEP 11: Redistribution for empty slots.
            logger.info("STEP 11: Running redistribution for empty slots")
            redistributed_slots = redistribute_empty_slots(
                assigned_slots,
                scaled_foods,
                slot_macro_targets,
                used_recipes,
            )

            if not is_plan_valid(redistributed_slots):
                if initial_valid:
                    redistributed_slots = assigned_slots
                else:
                    last_error = f"Not all meal slots filled after redistribution on attempt {attempt}"
                    logger.warning(last_error)
                    continue

            assigned_slots = redistributed_slots

            # STEP 11B: Single-slot swap local search to improve fallback quality.
            swap_tolerance = 1.35 if attempt >= 4 else 1.15
            optimized_slots, improved = improve_assignment_with_single_slot_swaps(
                assigned_slots,
                scaled_foods,
                slot_macro_targets,
                tolerance_multiplier=swap_tolerance,
            )
            if improved and is_plan_valid(optimized_slots):
                assigned_slots = optimized_slots
                logger.info("STEP 11B: Slot-swap optimization improved assignment")

            # Diversity layer: applied only after bucket generation/redistribution.
            logger.info("STEP 11C: Applying diversity-aware final selection")
            diversified_slots, diversity_meta = apply_diversity_aware_final_selection(
                assigned_slots=assigned_slots,
                recipes=scaled_foods,
                slot_targets=slot_macro_targets,
                meal_history=recent_meal_history,
                selection_seed=f"{history_seed}|attempt:{attempt}",
            )
            if is_plan_valid(diversified_slots):
                assigned_slots = diversified_slots
                repeat_count = int(diversity_meta.get("repeat_count", 0) or 0)
                new_meal_count = int(diversity_meta.get("new_meal_count", 0) or 0)
                logger.info(f"Diversity meta: repeats={repeat_count}, new={new_meal_count}")
                fallback_slots = diversity_meta.get("all_repeated_fallback_slots", [])
                if isinstance(fallback_slots, list) and fallback_slots:
                    global_warnings.append(
                        "Diversity relaxed for slots with only repeated candidates: "
                        + ", ".join(str(slot) for slot in fallback_slots)
                    )
            else:
                global_warnings.append(
                    "Diversity layer skipped because it could not preserve a fully valid slot assignment."
                )

            # Build structured plan
            structured_plan = {
                slot: {
                    "name": recipe.get("RecipeName", "Unknown"),
                    "calories": _coerce_float(recipe.get("Calories", 0)),
                    "protein": _coerce_float(recipe.get("Protein", 0)),
                    "carbs": _coerce_float(recipe.get("Carbohydrates", 0)),
                    "fat": _coerce_float(recipe.get("Fat", 0)),
                    "ingredients": recipe.get("Ingredients", ""),
                    "instructions": recipe.get("Instructions", ""),
                    "diet_type": recipe.get("DietType", "Unknown"),
                }
                for slot, recipe in assigned_slots.items()
                if recipe is not None
            }

            # STEP 12: Supplement solver after redistribution.
            logger.info("STEP 12: Filling macro gaps with supplements")
            target_macros = {
                "protein": macros.protein_grams,
                "carbohydrates": macros.carb_grams,
                "fat": macros.fat_grams,
            }
            supplement_result = fill_macro_gap(
                structured_plan,
                target_macros,
                supplements_dataset,
                user_diet=user_profile.diet_type,
                user_goal=user_profile.goal.value,
                allergies=user_profile.allergies or [],
                target_calories=calorie_target,
                calorie_tolerance=0.10,
            )

            # Build complete meal plan
            candidate_plan = _build_complete_meal_plan(
                user_profile=user_profile,
                bmr=bmr,
                tdee=tdee,
                calorie_target=calorie_target,
                macros=macros,
                structured_plan=structured_plan,
                supplements=supplement_result["supplements"],
                solver_mode="fallback" if attempt >= 4 or global_warnings else "strict",
                fallback_reason=(
                    "Applied deterministic fallback path due to strict constraint infeasibility"
                    if attempt >= 4 or global_warnings
                    else None
                ),
                attempt_count=attempt,
                warnings=[*global_warnings, *supplement_result["warnings"]],
            )

            score = abs(candidate_plan.total_calories - calorie_target)
            if score < best_candidate_score:
                best_candidate_score = score
                best_candidate_plan = candidate_plan

            # STEP 13: Final validation.
            logger.info("STEP 13: Final validation")
            is_valid = validate_generated_plan(
                candidate_plan,
                calorie_target,
                candidate_plan.macros,
                user_profile.diet_type,
                user_profile.allergies or [],
            )
            logger.info(f"Validation result: {'PASSED' if is_valid else 'FAILED'}")

            if not is_valid:
                last_error = f"Validation failed on attempt {attempt}"
                continue

            # STEP 14: Output formatting.
            logger.info("STEP 14: Formatting output")
            formatted_plan = format_meal_plan(structured_plan)
            final_plan = candidate_plan.model_copy(update={"meal_plan": formatted_plan})
            logger.info("✓ MEAL PLAN GENERATED SUCCESSFULLY")
            return final_plan

        except Exception as exc:
            last_error = str(exc)
            logger.warning(f"Attempt {attempt} failed: {last_error}")
            # Keep best_candidate_plan from previous attempts for fallback

    # Fallback: return best candidate if available
    if best_candidate_plan:
        logger.info("Returning best candidate from attempts with warnings")
        from services.nutrition_engine.meal_formatter import format_meal_plan

        # Use existing formatted plan if available; otherwise rebuild from meal items.
        formatted_plan = best_candidate_plan.meal_plan or {}
        if not formatted_plan:
            reconstructed = _reconstruct_structured_plan_from_complete_plan(best_candidate_plan)
            if len(reconstructed) == len(MEAL_SLOTS):
                try:
                    formatted_plan = format_meal_plan(reconstructed)
                except Exception:
                    formatted_plan = reconstructed

        warnings = list(best_candidate_plan.warnings or [])
        warnings.append("Returned best available plan after all retry attempts.")
        return best_candidate_plan.model_copy(
            update={
                "meal_plan": formatted_plan,
                "warnings": warnings,
                "solver_mode": "fallback",
                "fallback_reason": "No fully valid plan found within retry budget; returning best deterministic candidate",
                "attempt_count": MAX_REGENERATION_ATTEMPTS,
            }
        )

    raise HTTPException(
        status_code=400,
        detail=f"No valid meal plan generated after {MAX_REGENERATION_ATTEMPTS} attempts. Last error: {last_error}",
    )


def _build_complete_meal_plan(
    user_profile: UserProfile,
    bmr: float,
    tdee: float,
    calorie_target: float,
    macros: MacroSplit,
    structured_plan: Dict[str, Dict[str, Any]],
    supplements: Optional[List[Dict[str, Any]]] = None,
    solver_mode: str = "strict",
    fallback_reason: Optional[str] = None,
    attempt_count: int = 1,
    warnings: Optional[List[str]] = None,
) -> CompleteMealPlan:
    """Build complete meal plan object."""
    meals: List[MealItem] = []

    for slot in MEAL_SLOTS:
        meal_data = structured_plan.get(slot)
        if not meal_data:
            continue

        meals.append(
            MealItem(
                name=f"{slot.capitalize()} - {meal_data.get('name', 'Unknown')}",
                calories=_coerce_float(meal_data.get("calories", 0)),
                protein=_coerce_float(meal_data.get("protein", 0)),
                carbohydrates=_coerce_float(meal_data.get("carbs", meal_data.get("carbohydrates", 0))),
                fat=_coerce_float(meal_data.get("fat", 0)),
                ingredients=meal_data.get("ingredients", ""),
                instructions=meal_data.get("instructions", ""),
                diet_type=meal_data.get("diet_type", "Unknown"),
            )
        )

    supplement_items: List[SupplementItem] = []
    for supplement in (supplements or []):
        supplement_items.append(
            SupplementItem(
                name=str(supplement.get("name", "Supplement")),
                calories=_coerce_float(supplement.get("calories", 0)),
                protein=_coerce_float(supplement.get("protein", 0)),
                carbohydrates=_coerce_float(supplement.get("carbohydrates", 0)),
                fat=_coerce_float(supplement.get("fat", 0)),
                ingredients=str(supplement.get("ingredients", "")),
                instructions=str(supplement.get("instructions", "Consume as directed.")),
                diet_type=str(supplement.get("diet_type", "Unknown")),
            )
        )

    # Calculate totals
    total_calories = round(sum(m.calories for m in meals) + sum(s.calories for s in supplement_items), 2)
    total_protein = round(sum(m.protein for m in meals) + sum(s.protein for s in supplement_items), 2)
    total_carbs = round(sum(m.carbohydrates for m in meals) + sum(s.carbohydrates for s in supplement_items), 2)
    total_fat = round(sum(m.fat for m in meals) + sum(s.fat for s in supplement_items), 2)

    # Calculate accuracy
    calorie_accuracy = 100 - abs((total_calories - calorie_target) / calorie_target * 100) if calorie_target > 0 else 0
    calorie_accuracy = round(max(0.0, calorie_accuracy), 2)

    return CompleteMealPlan(
        user_profile={
            "age": user_profile.age,
            "weight": user_profile.weight,
            "height": user_profile.height,
            "sex": user_profile.sex.value,
            "activity_level": user_profile.activity_level.value,
            "goal": user_profile.goal.value,
            "diet_type": user_profile.diet_type,
            "allergies": user_profile.allergies or [],
            "last_meals": user_profile.last_meals or {},
        },
        bmr=round(bmr, 2),
        tdee=round(tdee, 2),
        calorie_target=round(calorie_target, 2),
        macros={
            "protein": macros.protein_grams,
            "carbohydrates": macros.carb_grams,
            "fat": macros.fat_grams,
        },
        macro_percentages={
            "protein": macros.protein_percentage,
            "carbohydrates": macros.carb_percentage,
            "fat": macros.fat_percentage,
        },
        meals=meals,
        supplements=supplement_items,
        meal_count=len(meals),
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fat=total_fat,
        calorie_accuracy=calorie_accuracy,
        goal=user_profile.goal.value,
        activity_level=user_profile.activity_level.value,
        solver_mode=solver_mode,
        fallback_reason=fallback_reason,
        attempt_count=attempt_count,
        warnings=warnings or [],
    )


def _reconstruct_structured_plan_from_complete_plan(plan: CompleteMealPlan) -> Dict[str, Dict[str, Any]]:
    """Rebuild structured slot data from CompleteMealPlan meal entries."""
    structured: Dict[str, Dict[str, Any]] = {}

    for meal in plan.meals:
        meal_name = str(meal.name or "")
        slot = ""

        if " - " in meal_name:
            slot = meal_name.split(" - ", 1)[0].strip().lower()

        if slot not in MEAL_SLOTS:
            continue

        display_name = meal_name.split(" - ", 1)[1].strip() if " - " in meal_name else meal_name.strip()
        structured[slot] = {
            "name": display_name or meal_name,
            "calories": _coerce_float(meal.calories, 0),
            "protein": _coerce_float(meal.protein, 0),
            "carbs": _coerce_float(meal.carbohydrates, 0),
            "fat": _coerce_float(meal.fat, 0),
            "ingredients": meal.ingredients or "",
            "instructions": meal.instructions or "",
            "diet_type": meal.diet_type or "Unknown",
        }

    return structured


# ============================================================================
# PUBLIC API
# ============================================================================


def create_meal_plan(user_profile: UserProfile) -> CompleteMealPlan:
    """Create a meal plan using the spec-compliant pipeline."""
    try:
        foods = load_food_dataset()
        return _generate_validated_meal_plan_spec_compliant(user_profile, foods)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected meal planner error")
        raise HTTPException(status_code=500, detail=f"Error creating meal plan: {exc}")


def create_meal_plan_response(user_profile: UserProfile) -> Dict[str, Any]:
    """Return the exact compact frontend payload for a meal plan request."""
    plan = create_meal_plan(user_profile)
    _persist_generated_meal_history(user_profile, plan)
    return plan.to_frontend_response()


def validate_user_profile(raw_profile: Dict[str, Any]) -> UserProfile:
    """Validate and normalize raw profile payload into UserProfile."""
    return UserProfile(**raw_profile)


def get_meal_plan_summary(plan: CompleteMealPlan) -> Dict[str, Any]:
    """Return a compact summary useful for testing/debugging."""
    return {
        "meal_count": plan.meal_count,
        "total_calories": plan.total_calories,
        "target_calories": plan.calorie_target,
        "accuracy": f"{plan.calorie_accuracy:.1f}%",
        "solver_mode": plan.solver_mode,
        "attempt_count": plan.attempt_count,
        "warnings": list(plan.warnings or []),
    }


def get_daily_meal_distribution(total_calories: float, _meal_count: int = 4) -> Dict[str, float]:
    """Return fixed 4-slot calorie distribution for the planner."""
    return split_calories_by_meal_slot(total_calories)


def compare_plan_to_targets(plan: CompleteMealPlan) -> Dict[str, Dict[str, float]]:
    """Compare achieved totals against calorie and macro targets."""
    def pct(actual: float, target: float) -> float:
        if target <= 0:
            return 0.0
        return round((actual / target) * 100.0, 2)

    return {
        "calories": {
            "actual": plan.total_calories,
            "target": plan.calorie_target,
            "percentage": pct(plan.total_calories, plan.calorie_target),
        },
        "protein": {
            "actual": plan.total_protein,
            "target": _coerce_float(plan.macros.get("protein", 0)),
            "percentage": pct(plan.total_protein, _coerce_float(plan.macros.get("protein", 0))),
        },
        "carbohydrates": {
            "actual": plan.total_carbs,
            "target": _coerce_float(plan.macros.get("carbohydrates", 0)),
            "percentage": pct(plan.total_carbs, _coerce_float(plan.macros.get("carbohydrates", 0))),
        },
        "fat": {
            "actual": plan.total_fat,
            "target": _coerce_float(plan.macros.get("fat", 0)),
            "percentage": pct(plan.total_fat, _coerce_float(plan.macros.get("fat", 0))),
        },
    }
