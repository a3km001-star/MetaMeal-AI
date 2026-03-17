"""Main service layer for the nutrition-engine meal planner.

This module orchestrates the full pipeline:

1. Load dataset
2. Calculate BMR
3. Calculate TDEE
4. Adjust calories for goal
5. Calculate macros
6. Filter foods by diet
7. Filter foods by allergies
8. Generate meal plan
9. Validate meal plan (with regeneration attempts)
10. Format response

The planner preserves internal rich models for validation and analytics while
also exposing a frontend-ready response shape through ``meal_plan`` and
``to_frontend_response()``.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from pydantic import BaseModel, Field, validator

from services.nutrition_engine.constraint_solver import (
    MealPlan,
    ensure_variety,
    filter_by_allergies,
    filter_by_diet,
    generate_meal_plan,
)
from services.nutrition_engine.macro_split import MacroSplit, calculate_macros
from services.nutrition_engine.metabolic_calculator import (
    ActivityLevel,
    FitnessGoal,
    Sex,
    calculate_bmr,
    calculate_tdee,
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
MEAL_SLOTS: Tuple[str, ...] = ("breakfast", "lunch", "dinner", "snack")
MAX_REGENERATION_ATTEMPTS = 5


def _sort_high_protein_foods(foods: List[Dict[str, Any]], calorie_target: float) -> List[Dict[str, Any]]:
    """Return foods ordered for protein-biased generation.

    Preference order:
    1. Closer to the average calories per meal
    2. Higher protein density
    3. Higher absolute protein
    """
    average_meal_calories = calorie_target / len(MEAL_SLOTS)
    return sorted(
        foods,
        key=lambda food: (
            abs(float(food.get("Calories", 0) or 0) - average_meal_calories),
            -(float(food.get("Protein", 0) or 0) / max(float(food.get("Calories", 1) or 1), 1.0)),
            -float(food.get("Protein", 0) or 0),
        ),
    )


def _score_totals(
    totals: Tuple[float, float, float, float],
    targets: Tuple[float, float, float, float],
) -> float:
    """Return a normalized deviation score for calories and macros."""
    weights = (1.1, 1.5, 1.0, 1.0)
    score = 0.0

    for value, target, weight in zip(totals, targets, weights):
        if target <= 0:
            continue

        deviation = abs(value - target) / target
        if value > target:
            deviation *= 1.15
        score += deviation * weight

    return score


def _generate_beam_search_plan(
    foods: List[Dict[str, Any]],
    calorie_target: float,
    macros: MacroSplit,
) -> MealPlan:
    """Generate a 4-meal plan by beam-searching meal-sized macro-balanced combinations."""
    if len(foods) < len(MEAL_SLOTS):
        raise ValueError("Not enough foods available to build a 4-meal plan")

    protein_floor = max(
        macros.protein_grams * 0.8,
        macros.protein_grams - min(30.0, macros.protein_grams * 0.2),
    )
    effective_targets = (
        calorie_target,
        protein_floor,
        macros.carb_grams,
        macros.fat_grams,
    )
    average_meal_calories = calorie_target / len(MEAL_SLOTS)

    ranked_foods = sorted(
        foods,
        key=lambda food: (
            abs(float(food.get("Calories", 0) or 0) - average_meal_calories),
            -(float(food.get("Protein", 0) or 0) / max(float(food.get("Calories", 1) or 1), 1.0)),
            -float(food.get("Protein", 0) or 0),
        ),
    )
    candidate_foods = ranked_foods[:80]

    beam: List[Tuple[List[Dict[str, Any]], Tuple[float, float, float, float], float]] = [
        ([], (0.0, 0.0, 0.0, 0.0), 0.0)
    ]

    for depth in range(len(MEAL_SLOTS)):
        progress = (depth + 1) / len(MEAL_SLOTS)
        partial_targets = (
            effective_targets[0] * progress,
            effective_targets[1] * progress,
            effective_targets[2] * progress,
            effective_targets[3] * progress,
        )
        next_beam: List[Tuple[List[Dict[str, Any]], Tuple[float, float, float, float], float]] = []

        for selected_meals, totals, _ in beam:
            used_names = {meal.get("RecipeName", "") for meal in selected_meals}

            for food in candidate_foods:
                recipe_name = str(food.get("RecipeName", ""))
                if recipe_name in used_names:
                    continue
                if not ensure_variety(selected_meals, food, max_same_ingredients=5):
                    continue

                food_totals = (
                    float(food.get("Calories", 0) or 0),
                    float(food.get("Protein", 0) or 0),
                    float(food.get("Carbohydrates", 0) or 0),
                    float(food.get("Fat", 0) or 0),
                )
                combined_totals = (
                    totals[0] + food_totals[0],
                    totals[1] + food_totals[1],
                    totals[2] + food_totals[2],
                    totals[3] + food_totals[3],
                )
                score = _score_totals(combined_totals, partial_targets)
                next_beam.append((selected_meals + [food], combined_totals, score))

        if not next_beam:
            raise ValueError("Beam search could not assemble a valid 4-meal combination")

        next_beam.sort(key=lambda state: state[2])
        beam = next_beam[:250]

    best_meals, best_totals, _ = min(
        beam,
        key=lambda state: _score_totals(state[1], effective_targets),
    )

    total_calories, total_protein, total_carbs, total_fat = best_totals
    deviation = abs(total_calories - calorie_target) / calorie_target if calorie_target else 1.0

    return MealPlan(
        meals=best_meals,
        total_calories=round(total_calories, 2),
        total_protein=round(total_protein, 2),
        total_carbs=round(total_carbs, 2),
        total_fat=round(total_fat, 2),
        target_calories=calorie_target,
        calorie_deviation=round(deviation * 100, 2),
        meal_count=len(best_meals),
    )


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

    @validator("weight")
    def validate_weight(cls, value: float) -> float:
        if value < 30 or value > 300:
            raise ValueError("Weight must be between 30 and 300 kg")
        return value

    @validator("height")
    def validate_height(cls, value: float) -> float:
        if value < 100 or value > 250:
            raise ValueError("Height must be between 100 and 250 cm")
        return value


class MealItem(BaseModel):
    """Internal normalized meal object used for validation and analytics."""

    name: str = Field(..., description="Meal display name")
    calories: float = Field(..., description="Calories (kcal)")
    protein: float = Field(..., description="Protein in grams")
    carbohydrates: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")
    ingredients: str = Field(..., description="Ingredients string")
    instructions: str = Field(..., description="Instructions string")
    diet_type: str = Field(..., description="Diet classification")


class SupplementItem(BaseModel):
    """Normalized supplement item used to fill macro gaps."""

    name: str = Field(..., description="Supplement display name")
    calories: float = Field(..., description="Calories (kcal)")
    protein: float = Field(..., description="Protein in grams")
    carbohydrates: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")
    ingredients: str = Field(..., description="Ingredients string")
    instructions: str = Field(..., description="Instructions string")
    diet_type: str = Field(..., description="Diet classification")


class CompleteMealPlan(BaseModel):
    """Detailed meal-plan response with both internal and frontend-ready data."""

    user_profile: Dict[str, Any] = Field(..., description="User profile used to build the plan")
    bmr: float = Field(..., description="Basal metabolic rate")
    tdee: float = Field(..., description="Total daily energy expenditure")
    calorie_target: float = Field(..., description="Daily calorie target")
    macros: Dict[str, float] = Field(..., description="Internal macro targets")
    macro_percentages: Dict[str, float] = Field(..., description="Macro split percentages")
    meals: List[MealItem] = Field(..., description="Normalized meals for validation")
    supplements: List[SupplementItem] = Field(default_factory=list, description="Supplement additions")
    meal_plan: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Frontend-ready structured meal plan",
    )
    meal_count: int = Field(..., description="Number of meals selected")
    total_calories: float = Field(..., description="Total meal calories")
    total_protein: float = Field(..., description="Total protein")
    total_carbs: float = Field(..., description="Total carbohydrates")
    total_fat: float = Field(..., description="Total fat")
    calorie_accuracy: float = Field(..., description="Calorie accuracy percentage")
    goal: str = Field(..., description="Goal name")
    activity_level: str = Field(..., description="Activity level name")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal planner warnings")

    def to_frontend_response(self) -> Dict[str, Any]:
        """Return the exact compact payload expected by the frontend."""
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
                    "name": supplement.name,
                    "protein": supplement.protein,
                    "calories": supplement.calories,
                }
                for supplement in self.supplements
            ],
        }

        if self.warnings:
            response["warnings"] = self.warnings

        return response


def _adjust_calories_for_goal(tdee: float, goal: FitnessGoal, sex: Sex) -> float:
    """Apply goal-based calorie adjustment with sex-specific minimum floors."""
    if tdee <= 0:
        raise HTTPException(status_code=400, detail="TDEE must be positive")

    adjustment = GOAL_ADJUSTMENTS.get(goal)
    if adjustment is None:
        raise HTTPException(status_code=400, detail=f"Unsupported goal: {goal}")

    calorie_target = tdee * (1 + adjustment)
    calorie_target = max(calorie_target, MIN_CALORIES_BY_SEX.get(sex, 1200))
    return round(calorie_target, 2)


def _normalize_raw_meal(raw_meal: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw solver output into a slot-based meal dictionary."""
    return {
        "name": raw_meal.get("name") or raw_meal.get("RecipeName") or "Unknown Meal",
        "calories": round(float(raw_meal.get("calories", raw_meal.get("Calories", 0)) or 0), 2),
        "protein": round(float(raw_meal.get("protein", raw_meal.get("Protein", 0)) or 0), 2),
        "carbs": round(float(raw_meal.get("carbs", raw_meal.get("Carbohydrates", 0)) or 0), 2),
        "fat": round(float(raw_meal.get("fat", raw_meal.get("Fat", 0)) or 0), 2),
        "ingredients": raw_meal.get("ingredients") or raw_meal.get("Ingredients") or "",
        "instructions": raw_meal.get("instructions") or raw_meal.get("Instructions") or "",
        "diet_type": raw_meal.get("diet_type") or raw_meal.get("DietType") or "Unknown",
    }


def _structure_solver_plan(solver_plan: MealPlan) -> Dict[str, Dict[str, Any]]:
    """Map solver meal order to breakfast/lunch/dinner/snack slots."""
    if solver_plan.meal_count != len(MEAL_SLOTS) or len(solver_plan.meals) != len(MEAL_SLOTS):
        raise ValueError(
            f"Meal plan must contain exactly {len(MEAL_SLOTS)} meals, got {len(solver_plan.meals)}"
        )

    structured_plan: Dict[str, Dict[str, Any]] = {}
    for slot, raw_meal in zip(MEAL_SLOTS, solver_plan.meals):
        structured_plan[slot] = _normalize_raw_meal(raw_meal)

    return structured_plan


def _calculate_plan_totals(structured_plan: Dict[str, Dict[str, Any]]) -> Tuple[float, float, float, float]:
    """Calculate calorie and macro totals from the structured raw meal plan."""
    total_calories = round(sum(meal["calories"] for meal in structured_plan.values()), 2)
    total_protein = round(sum(meal["protein"] for meal in structured_plan.values()), 2)
    total_carbs = round(sum(meal["carbs"] for meal in structured_plan.values()), 2)
    total_fat = round(sum(meal["fat"] for meal in structured_plan.values()), 2)
    return total_calories, total_protein, total_carbs, total_fat


def _calculate_supplement_totals(supplements: List[Dict[str, Any]]) -> Tuple[float, float, float, float]:
    """Calculate calorie and macro totals from selected supplements."""
    total_calories = round(sum(float(item.get("calories", 0) or 0) for item in supplements), 2)
    total_protein = round(sum(float(item.get("protein", 0) or 0) for item in supplements), 2)
    total_carbs = round(sum(float(item.get("carbohydrates", 0) or 0) for item in supplements), 2)
    total_fat = round(sum(float(item.get("fat", 0) or 0) for item in supplements), 2)
    return total_calories, total_protein, total_carbs, total_fat


def _build_complete_meal_plan(
    user_profile: UserProfile,
    bmr: float,
    tdee: float,
    calorie_target: float,
    macros: MacroSplit,
    structured_plan: Dict[str, Dict[str, Any]],
    supplements: Optional[List[Dict[str, Any]]] = None,
    formatted_plan: Optional[Dict[str, Dict[str, Any]]] = None,
    warnings: Optional[List[str]] = None,
) -> CompleteMealPlan:
    """Build the internal detailed plan object used by validation and responses."""
    meals: List[MealItem] = []
    normalized_supplements = supplements or []
    planner_warnings = warnings or []

    for slot in MEAL_SLOTS:
        meal = structured_plan[slot]
        meals.append(
            MealItem(
                name=f"{slot.capitalize()} - {meal['name']}",
                calories=meal["calories"],
                protein=meal["protein"],
                carbohydrates=meal["carbs"],
                fat=meal["fat"],
                ingredients=meal["ingredients"],
                instructions=meal["instructions"],
                diet_type=meal.get("diet_type", "Unknown"),
            )
        )

    supplement_items: List[SupplementItem] = []
    for supplement in normalized_supplements:
        supplement_items.append(
            SupplementItem(
                name=str(supplement.get("name", "Supplement")),
                calories=float(supplement.get("calories", 0) or 0),
                protein=float(supplement.get("protein", 0) or 0),
                carbohydrates=float(supplement.get("carbohydrates", 0) or 0),
                fat=float(supplement.get("fat", 0) or 0),
                ingredients=str(supplement.get("ingredients", "")),
                instructions=str(supplement.get("instructions", "Consume as directed.")),
                diet_type=str(supplement.get("diet_type", "Unknown")),
            )
        )

    meal_calories, meal_protein, meal_carbs, meal_fat = _calculate_plan_totals(structured_plan)
    supplement_calories, supplement_protein, supplement_carbs, supplement_fat = _calculate_supplement_totals(
        normalized_supplements
    )

    total_calories = round(meal_calories + supplement_calories, 2)
    total_protein = round(meal_protein + supplement_protein, 2)
    total_carbs = round(meal_carbs + supplement_carbs, 2)
    total_fat = round(meal_fat + supplement_fat, 2)

    if calorie_target > 0:
        raw_accuracy = 100 - abs((total_calories - calorie_target) / calorie_target * 100)
        calorie_accuracy = round(max(0.0, raw_accuracy), 2)
    else:
        calorie_accuracy = 0.0

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
        meal_plan=formatted_plan,
        meal_count=len(meals),
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fat=total_fat,
        calorie_accuracy=calorie_accuracy,
        goal=user_profile.goal.value,
        activity_level=user_profile.activity_level.value,
        warnings=planner_warnings,
    )


def _generate_validated_meal_plan(user_profile: UserProfile, foods: List[Dict[str, Any]]) -> CompleteMealPlan:
    """Generate, validate, and format a meal plan using the full pipeline."""
    from services.nutrition_engine.meal_formatter import format_meal_plan
    from services.nutrition_engine.meal_validator import validate_meal_plan as validate_generated_plan
    from services.nutrition_engine.supplement_solver import fill_macro_gap, load_supplements

    if not foods:
        raise HTTPException(status_code=500, detail="Dataset is empty")

    logger.info("dataset loaded")

    bmr = calculate_bmr(user_profile.age, user_profile.weight, user_profile.height, user_profile.sex)
    logger.info("BMR calculated")

    tdee = calculate_tdee(bmr, user_profile.activity_level)
    calorie_target = _adjust_calories_for_goal(tdee, user_profile.goal, user_profile.sex)
    macros = calculate_macros(
        calories=calorie_target,
        goal=user_profile.goal,
        weight_kg=user_profile.weight,
    )

    filtered_foods = filter_by_diet(foods, user_profile.diet_type)
    filtered_foods = filter_by_allergies(filtered_foods, user_profile.allergies or [])
    supplements_dataset = load_supplements()

    if not filtered_foods:
        raise HTTPException(
            status_code=400,
            detail="No foods available after applying diet and allergy filters",
        )

    last_error = "Validation failed"

    for attempt in range(1, MAX_REGENERATION_ATTEMPTS + 1):
        try:
            high_protein_bias = attempt >= 2
            candidate_foods = _sort_high_protein_foods(filtered_foods, calorie_target) if high_protein_bias else list(filtered_foods)
            if attempt >= 3:
                solver_plan = _generate_beam_search_plan(candidate_foods, calorie_target, macros)
            else:
                solver_plan = generate_meal_plan(
                    foods=candidate_foods,
                    calorie_target=calorie_target,
                    max_meals=4,
                    calorie_tolerance=0.10,
                    max_attempts=200 if high_protein_bias else 100,
                    shuffle=not high_protein_bias,
                )
            logger.info("meal plan generated")

            structured_plan = _structure_solver_plan(solver_plan)
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
                allergies=user_profile.allergies or [],
                target_calories=calorie_target,
                calorie_tolerance=0.10,
            )
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

            is_valid = validate_generated_plan(
                candidate_plan,
                calorie_target,
                candidate_plan.macros,
                user_profile.diet_type,
                user_profile.allergies or [],
            )
            logger.info("validation result: %s", "passed" if is_valid else "failed")

            if not is_valid:
                last_error = f"Generated meal plan failed validation on attempt {attempt}"
                continue

            formatted_plan = format_meal_plan(structured_plan)
            final_plan = candidate_plan.copy(update={"meal_plan": formatted_plan})
            logger.info("final plan returned")
            return final_plan

        except HTTPException as exc:
            last_error = str(exc.detail)
            logger.warning(
                "Meal plan attempt %d/%d failed: %s",
                attempt,
                MAX_REGENERATION_ATTEMPTS,
                last_error,
            )
        except (TypeError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "Meal plan attempt %d/%d failed: %s",
                attempt,
                MAX_REGENERATION_ATTEMPTS,
                last_error,
            )

    raise HTTPException(
        status_code=400,
        detail=(
            f"No valid meal plan generated after {MAX_REGENERATION_ATTEMPTS} attempts. "
            f"Last error: {last_error}"
        ),
    )


def create_meal_plan(user_profile: UserProfile) -> CompleteMealPlan:
    """Create a meal plan using the full orchestration pipeline."""
    try:
        foods = load_food_dataset()
        return _generate_validated_meal_plan(user_profile, foods)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected meal planner error")
        raise HTTPException(status_code=500, detail=f"Error creating meal plan: {exc}")


def create_meal_plan_response(user_profile: UserProfile) -> Dict[str, Any]:
    """Return the exact compact frontend payload for a meal plan request."""
    return create_meal_plan(user_profile).to_frontend_response()


def get_meal_plan_summary(meal_plan: CompleteMealPlan) -> Dict[str, Any]:
    """Return a compact summary of a generated detailed meal plan."""
    return {
        "meal_count": meal_plan.meal_count,
        "total_calories": meal_plan.total_calories,
        "calorie_target": meal_plan.calorie_target,
        "accuracy": f"{meal_plan.calorie_accuracy}%",
        "macros": meal_plan.macros,
        "goal": meal_plan.goal,
        "meal_names": [meal.name for meal in meal_plan.meals],
    }


def validate_user_profile(profile_data: Dict[str, Any]) -> UserProfile:
    """Validate raw request payload into a ``UserProfile`` model."""
    try:
        return UserProfile(**profile_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid user profile: {exc}")


def regenerate_meal_plan_with_changes(
    user_profile: UserProfile,
    exclude_meals: Optional[List[str]] = None,
    prefer_high_protein: bool = False,
) -> CompleteMealPlan:
    """Regenerate a meal plan after excluding meals or preferring protein-dense foods."""
    try:
        foods = load_food_dataset()

        if exclude_meals:
            excluded = set(exclude_meals)
            foods = [
                food for food in foods
                if food.get("RecipeName", "") not in excluded
            ]

        if prefer_high_protein:
            foods = sorted(
                foods,
                key=lambda food: (food.get("Protein", 0) / max(food.get("Calories", 1), 1)),
                reverse=True,
            )

        return _generate_validated_meal_plan(user_profile, foods)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected meal regeneration error")
        raise HTTPException(status_code=500, detail=f"Error regenerating meal plan: {exc}")


def get_daily_meal_distribution(calorie_target: float, meal_count: int = 4) -> Dict[str, Dict[str, float]]:
    """Return a suggested calorie distribution across meals."""
    if meal_count <= 0:
        raise ValueError(f"meal_count must be > 0, got {meal_count}")

    if meal_count == 3:
        return {
            "breakfast": {"min": calorie_target * 0.25, "max": calorie_target * 0.30},
            "lunch": {"min": calorie_target * 0.35, "max": calorie_target * 0.40},
            "dinner": {"min": calorie_target * 0.30, "max": calorie_target * 0.35},
        }
    if meal_count == 4:
        return {
            "breakfast": {"min": calorie_target * 0.20, "max": calorie_target * 0.25},
            "lunch": {"min": calorie_target * 0.30, "max": calorie_target * 0.35},
            "snack": {"min": calorie_target * 0.10, "max": calorie_target * 0.15},
            "dinner": {"min": calorie_target * 0.30, "max": calorie_target * 0.35},
        }
    if meal_count == 5:
        return {
            "breakfast": {"min": calorie_target * 0.20, "max": calorie_target * 0.25},
            "morning_snack": {"min": calorie_target * 0.08, "max": calorie_target * 0.12},
            "lunch": {"min": calorie_target * 0.30, "max": calorie_target * 0.35},
            "evening_snack": {"min": calorie_target * 0.08, "max": calorie_target * 0.12},
            "dinner": {"min": calorie_target * 0.25, "max": calorie_target * 0.30},
        }

    per_meal = calorie_target / meal_count
    return {
        f"meal_{index + 1}": {"min": per_meal * 0.8, "max": per_meal * 1.2}
        for index in range(meal_count)
    }


def compare_plan_to_targets(meal_plan: CompleteMealPlan) -> Dict[str, Any]:
    """Compare actual totals against calorie and macro targets."""
    return {
        "calories": {
            "target": meal_plan.calorie_target,
            "actual": meal_plan.total_calories,
            "difference": meal_plan.total_calories - meal_plan.calorie_target,
            "percentage": round(
                (meal_plan.total_calories / meal_plan.calorie_target) * 100,
                2,
            ) if meal_plan.calorie_target > 0 else 0,
        },
        "protein": {
            "target": meal_plan.macros["protein"],
            "actual": meal_plan.total_protein,
            "difference": meal_plan.total_protein - meal_plan.macros["protein"],
            "percentage": round(
                (meal_plan.total_protein / meal_plan.macros["protein"]) * 100,
                2,
            ) if meal_plan.macros["protein"] > 0 else 0,
        },
        "carbohydrates": {
            "target": meal_plan.macros["carbohydrates"],
            "actual": meal_plan.total_carbs,
            "difference": meal_plan.total_carbs - meal_plan.macros["carbohydrates"],
            "percentage": round(
                (meal_plan.total_carbs / meal_plan.macros["carbohydrates"]) * 100,
                2,
            ) if meal_plan.macros["carbohydrates"] > 0 else 0,
        },
        "fat": {
            "target": meal_plan.macros["fat"],
            "actual": meal_plan.total_fat,
            "difference": meal_plan.total_fat - meal_plan.macros["fat"],
            "percentage": round(
                (meal_plan.total_fat / meal_plan.macros["fat"]) * 100,
                2,
            ) if meal_plan.macros["fat"] > 0 else 0,
        },
        "overall_accuracy": meal_plan.calorie_accuracy,
    }
