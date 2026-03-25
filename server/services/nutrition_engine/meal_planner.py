"""Main service layer for the nutrition-engine meal planner (SPEC-COMPLIANT).

This module implements the specification-compliant 11-step meal planning algorithm:

1. Metabolic Base: Calculate BMR, TDEE, calorie target
2. Carb Baseline: Subtract 390 kcal from total
3. Filtering: Apply diet type and allergy filters
4. Age-Based Scaling: Apply multiply_factor (1.6-2.5)
5. Meal Split: Distribute calories by slot (25%/35%/30%/10%)
6. Bucket Assignment: Assign recipes to meal slots by error
7. Validity Check: Ensure all 4 slots filled
8. Redistribution: Move items between buckets if needed
9. Supplement Solver: Fill macro gaps
10. Final Validation: Ensure targets met
11. Output: Return formatted JSON

The planner is deterministic, algorithmic, and guarantees output.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

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
    apply_carb_baseline,
    assign_recipe_to_slot,
    get_age_multiply_factor,
    is_plan_valid,
    scale_recipe_by_factor,
    sort_recipes_for_assignment,
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


def _normalize_food_for_multiply_factor(food: Dict[str, Any]) -> Dict[str, Any]:
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
    """Generate meal plan using spec-compliant 11-step algorithm."""
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

    # STEP 3: Filtering
    logger.info("STEP 3: Filtering by diet and allergies")
    prepared_foods = _prepare_foods_for_profile_spec_compliant(foods, user_profile)
    filtered_foods = filter_by_diet(prepared_foods, user_profile.diet_type)
    filtered_foods = filter_by_allergies(filtered_foods, user_profile.allergies or [])
    logger.info(f"After filtering: {len(filtered_foods)} foods available")

    if not filtered_foods:
        raise HTTPException(
            status_code=400,
            detail="No foods available after applying diet and allergy filters",
        )

    supplements_dataset = load_supplements()
    best_candidate_plan: Optional[CompleteMealPlan] = None
    last_error = "Validation failed"

    # Retry loop with fallback strategies
    for attempt in range(1, MAX_REGENERATION_ATTEMPTS + 1):
        try:
            logger.info(f"ATTEMPT {attempt}/{MAX_REGENERATION_ATTEMPTS}")

            # STEP 4: Age-Based Scaling (already done in food prep, but adjust for fallback)
            if attempt >= 4:
                logger.info("FALLBACK: Using increased multiply_factor")
                multiply_factor = 2.5
                age_factor = get_age_multiply_factor(user_profile.age)
                if not age_factor or age_factor <= 0:
                    logger.warning(f"Invalid age_factor {age_factor} for age {user_profile.age}, using 1.6 as fallback")
                    age_factor = 1.6
                scaled_foods = [scale_recipe_by_factor(f, multiply_factor / age_factor) for f in filtered_foods]
            else:
                scaled_foods = list(filtered_foods)

            # STEP 5: Meal Split
            logger.info("STEP 5: Calculating meal slot targets")
            slot_calorie_targets = split_calories_by_meal_slot(adjusted_calories)
            slot_macro_targets = split_macros_by_meal_slot(slot_calorie_targets, {
                "protein": macros.protein_grams,
                "carbohydrates": macros.carb_grams,
                "fat": macros.fat_grams,
            })
            logger.info(f"Slot targets: {slot_calorie_targets}")

            # STEP 6: Bucket Assignment
            logger.info("STEP 6: Assigning recipes to meal slots")
            sorted_foods = sort_recipes_for_assignment(scaled_foods, slot_macro_targets)
            assigned_slots: Dict[str, Optional[Dict[str, Any]]] = {slot: None for slot in MEAL_SLOTS}
            used_recipes: Set[int] = set()  # Track by object id instead of name

            for recipe in sorted_foods:
                assigned_slot = assign_recipe_to_slot(
                    recipe,
                    slot_macro_targets,
                    assigned_slots,
                    used_recipes,
                )
                if assigned_slot:
                    assigned_slots[assigned_slot] = recipe
                    used_recipes.add(id(recipe))  # Use object id for unique identification
                    logger.info(f"  Assigned to {assigned_slot}: {recipe.get('RecipeName')}")

            # STEP 7: Validity Check
            logger.info("STEP 7: Checking plan validity")
            if not is_plan_valid(assigned_slots):
                last_error = f"Not all meal slots filled on attempt {attempt}"
                logger.warning(last_error)
                continue

            # STEP 8: Redistribution (if needed - skip in this version since 1 recipe per slot)
            logger.info("STEP 8: Redistribution check (not needed in 1-recipe-per-slot mode)")

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

            # STEP 9: Supplement Solver
            logger.info("STEP 9: Filling macro gaps with supplements")
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
                warnings=supplement_result["warnings"],
            )

            # STEP 10: Final Validation
            logger.info("STEP 10: Final validation")
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
                best_candidate_plan = candidate_plan  # Keep as fallback
                continue

            # STEP 11: Output
            logger.info("STEP 11: Formatting output")
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
        # Use the meal_plan already in best_candidate_plan or reconstruct from it
        formatted_plan = best_candidate_plan.meal_plan or {}
        warnings = list(best_candidate_plan.warnings or [])
        warnings.append("Returned best available plan after all retry attempts.")
        return best_candidate_plan.model_copy(
            update={"meal_plan": formatted_plan, "warnings": warnings}
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
        warnings=warnings or [],
    )


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
    return create_meal_plan(user_profile).to_frontend_response()
