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
from pydantic import BaseModel, Field, field_validator

from services.nutrition_engine.constraint_solver import (
    MealPlan,
    ensure_variety,
    filter_by_allergies,
    filter_by_diet,
    generate_macro_aware_meal_plan,
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
MIN_PORTION_GRAMS = 80.0
PORTION_MULTIPLIERS: Tuple[float, ...] = (1.0, 1.5, 2.0, 2.5, 3.0)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    """Safely convert incoming values to float."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_age_based_single_portion_grams(age: int) -> float:
    """Return a single-portion gram weight derived from age.

    Dataset nutrition values are treated as per-100g values. This function
    provides the per-user portion size used to scale those values into actual
    consumed meal macros.
    """
    if age <= 18:
        return 90.0
    if age <= 29:
        return 110.0
    if age <= 44:
        return 105.0
    if age <= 59:
        return 95.0
    return 85.0


def _scale_from_per_100g(value_per_100g: float, portion_grams: float) -> float:
    """Scale a per-100g nutrient value to a concrete portion size."""
    return round((value_per_100g / 100.0) * portion_grams, 2)


def _normalize_food_for_portion_scaling(food: Dict[str, Any], portion_grams: float) -> Dict[str, Any]:
    """Normalize dataset row and scale macros from per-100g to actual portion."""
    calories_per_100g = _coerce_float(food.get("Calories", food.get("Calories (kcal)", 0)))
    protein_per_100g = _coerce_float(food.get("Protein", food.get("Protein(g)", 0)))
    carbs_per_100g = _coerce_float(food.get("Carbohydrates", food.get("Carbohydrates (g)", 0)))
    fat_per_100g = _coerce_float(food.get("Fat", food.get("Fat (g)", 0)))

    normalized: Dict[str, Any] = {
        "RecipeName": food.get("RecipeName", "Unknown Meal"),
        "DisplayName": food.get("RecipeName", "Unknown Meal"),
        "Ingredients": food.get("Ingredients") or food.get("Cleaned-Ingredients") or "",
        "Instructions": food.get("Instructions") or food.get("TranslatedInstructions") or "",
        "DietType": food.get("DietType") or food.get("vegornonveg") or "Unknown",
        "Calories": _scale_from_per_100g(calories_per_100g, portion_grams),
        "Protein": _scale_from_per_100g(protein_per_100g, portion_grams),
        "Carbohydrates": _scale_from_per_100g(carbs_per_100g, portion_grams),
        "Fat": _scale_from_per_100g(fat_per_100g, portion_grams),
        "portion_grams": round(portion_grams, 2),
        "serving_multiplier": 1.0,
        "base_recipe_name": food.get("RecipeName", "Unknown Meal"),
        "macro_values_per_100g": {
            "Calories": round(calories_per_100g, 4),
            "Protein": round(protein_per_100g, 4),
            "Carbohydrates": round(carbs_per_100g, 4),
            "Fat": round(fat_per_100g, 4),
        },
    }

    return normalized


def _is_reasonable_nutrition_row(normalized: Dict[str, Any]) -> bool:
    """Return False for obviously invalid/outlier macro rows.

    This protects the planner from malformed dataset values (for example,
    accidental 10x/100x protein entries) that can derail optimization.
    """
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


def _expand_food_portion_variants(base_foods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create meal variants at 1x/1.5x/2x/2.5x/3x serving multipliers."""
    expanded: List[Dict[str, Any]] = []

    for food in base_foods:
        base_name = str(food.get("RecipeName", "Unknown Meal"))
        base_calories = _coerce_float(food.get("Calories", 0))
        base_protein = _coerce_float(food.get("Protein", 0))
        base_carbs = _coerce_float(food.get("Carbohydrates", 0))
        base_fat = _coerce_float(food.get("Fat", 0))
        base_portion = _coerce_float(food.get("portion_grams", 0))

        for mult in PORTION_MULTIPLIERS:
            variant = dict(food)
            variant["Calories"] = round(base_calories * mult, 2)
            variant["Protein"] = round(base_protein * mult, 2)
            variant["Carbohydrates"] = round(base_carbs * mult, 2)
            variant["Fat"] = round(base_fat * mult, 2)
            variant["portion_grams"] = round(base_portion * mult, 2)
            variant["serving_multiplier"] = mult
            variant["base_recipe_name"] = base_name
            variant["DisplayName"] = f"{base_name} ({mult:.1f}x)" if mult != 1.0 else base_name

            if _coerce_float(variant.get("Calories", 0), 0) <= 1300 and _is_reasonable_nutrition_row(variant):
                expanded.append(variant)

    return expanded


def _prepare_foods_for_profile(foods: List[Any], user_profile: "UserProfile") -> List[Dict[str, Any]]:
    """Convert dataset rows into age-adjusted portion nutrition rows."""
    portion_grams = max(_get_age_based_single_portion_grams(user_profile.age), MIN_PORTION_GRAMS)
    normalized_foods: List[Dict[str, Any]] = []

    for row in foods:
        if isinstance(row, dict):
            normalized = _normalize_food_for_portion_scaling(row, portion_grams)
            if (
                normalized["RecipeName"].strip()
                and normalized["Ingredients"].strip()
                and _is_reasonable_nutrition_row(normalized)
            ):
                normalized_foods.append(normalized)
            continue

        if isinstance(row, list):
            # Some dataset snapshots may contain a nested list item; flatten it.
            for nested in row:
                if isinstance(nested, dict):
                    normalized = _normalize_food_for_portion_scaling(nested, portion_grams)
                    if (
                        normalized["RecipeName"].strip()
                        and normalized["Ingredients"].strip()
                        and _is_reasonable_nutrition_row(normalized)
                    ):
                        normalized_foods.append(normalized)
            continue

    return _expand_food_portion_variants(normalized_foods)


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
        key=lambda food: abs(float(food.get("Calories", 0) or 0) - average_meal_calories),
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
            used_names = {meal.get("base_recipe_name") or meal.get("RecipeName", "") for meal in selected_meals}

            for food in candidate_foods:
                recipe_name = str(food.get("base_recipe_name") or food.get("RecipeName", ""))
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


def _compute_base_meal_target_ratio(user_profile: UserProfile, attempt: int) -> float:
    """Compute an adaptive calorie ratio reserved for meal selection before supplements."""
    ratio = 0.90 if attempt <= 3 else 0.88
    diet = (user_profile.diet_type or "").strip().lower()

    if diet in {"veg", "vegetarian", "vegan"}:
        ratio += 0.03
    if user_profile.goal == FitnessGoal.MAINTENANCE:
        ratio += 0.03
    elif user_profile.goal == FitnessGoal.MUSCLE_GAIN:
        ratio += 0.02
    if attempt >= 4:
        ratio += 0.05

    return min(max(ratio, 0.88), 1.0)


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


def _adapt_macros_for_diet_constraints(
    macros: MacroSplit,
    calorie_target: float,
    user_profile: UserProfile,
) -> Tuple[MacroSplit, List[str]]:
    """Adjust macro targets for constrained diet cases to improve feasibility."""
    warnings: List[str] = []
    diet_key = (user_profile.diet_type or "").strip().lower()

    if diet_key == "vegan" and user_profile.goal == FitnessGoal.MAINTENANCE:
        # Vegan plans in this dataset tend to be relatively higher in fat and lower in carbs.
        # Keep protein target unchanged but re-balance remaining calories toward fat.
        protein_grams = float(macros.protein_grams)
        protein_calories = protein_grams * 4
        fat_percentage = max(float(macros.fat_percentage), 35.0)
        fat_calories = calorie_target * (fat_percentage / 100.0)
        fat_grams = round(fat_calories / 9.0, 1)
        carb_calories = max(0.0, calorie_target - protein_calories - fat_calories)
        carb_grams = round(carb_calories / 4.0, 1)
        protein_percentage = round((protein_calories / calorie_target) * 100, 1) if calorie_target > 0 else 0.0
        carb_percentage = round((carb_calories / calorie_target) * 100, 1) if calorie_target > 0 else 0.0

        adjusted = macros.model_copy(
            update={
                "carb_grams": carb_grams,
                "fat_grams": fat_grams,
                "carb_calories": round(carb_calories, 1),
                "fat_calories": round(fat_calories, 1),
                "protein_percentage": protein_percentage,
                "carb_percentage": carb_percentage,
                "fat_percentage": round(fat_percentage, 1),
            }
        )
        warnings.append("Macro targets adjusted for vegan maintenance feasibility (higher fat, lower carbs).")
        return adjusted, warnings

    return macros, warnings


def _normalize_raw_meal(raw_meal: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw solver output into a slot-based meal dictionary."""
    return {
        "name": raw_meal.get("name") or raw_meal.get("DisplayName") or raw_meal.get("RecipeName") or "Unknown Meal",
        "calories": round(float(raw_meal.get("calories", raw_meal.get("Calories", 0)) or 0), 2),
        "protein": round(float(raw_meal.get("protein", raw_meal.get("Protein", 0)) or 0), 2),
        "carbs": round(float(raw_meal.get("carbs", raw_meal.get("Carbohydrates", 0)) or 0), 2),
        "fat": round(float(raw_meal.get("fat", raw_meal.get("Fat", 0)) or 0), 2),
        "ingredients": raw_meal.get("ingredients") or raw_meal.get("Ingredients") or "",
        "instructions": raw_meal.get("instructions") or raw_meal.get("Instructions") or "",
        "diet_type": raw_meal.get("diet_type") or raw_meal.get("DietType") or "Unknown",
        "portion_grams": round(float(raw_meal.get("portion_grams", 0) or 0), 2),
        "serving_multiplier": round(float(raw_meal.get("serving_multiplier", 1.0) or 1.0), 2),
        "macro_values_per_100g": raw_meal.get("macro_values_per_100g", {}),
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
    macros, planner_macro_warnings = _adapt_macros_for_diet_constraints(macros, calorie_target, user_profile)

    prepared_foods = _prepare_foods_for_profile(foods, user_profile)
    filtered_foods = filter_by_diet(prepared_foods, user_profile.diet_type)
    filtered_foods = filter_by_allergies(filtered_foods, user_profile.allergies or [])
    supplements_dataset = load_supplements()

    if not filtered_foods:
        raise HTTPException(
            status_code=400,
            detail="No foods available after applying diet and allergy filters",
        )

    last_error = "Validation failed"
    best_candidate_plan: Optional[CompleteMealPlan] = None
    best_candidate_structure: Optional[Dict[str, Dict[str, Any]]] = None
    best_candidate_score = float("inf")

    for attempt in range(1, MAX_REGENERATION_ATTEMPTS + 1):
        try:
            diet_key = (user_profile.diet_type or "").strip().lower()
            carb_priority_mode = (diet_key in {"vegan"}) and (user_profile.goal == FitnessGoal.MAINTENANCE)
            candidate_foods = list(filtered_foods)
            # Leave headroom so protein supplements can fill gaps without breaching calorie bounds.
            base_target_ratio = _compute_base_meal_target_ratio(user_profile, attempt)
            base_meal_calorie_target = calorie_target * base_target_ratio
            if attempt >= 4:
                solver_plan = _generate_beam_search_plan(candidate_foods, base_meal_calorie_target, macros)
            elif attempt >= 2:
                macro_aware_tolerance = 0.15 if carb_priority_mode else (0.12 if attempt == 2 else 0.15)
                solver_plan = generate_macro_aware_meal_plan(
                    foods=candidate_foods,
                    calorie_target=base_meal_calorie_target,
                    protein_target=macros.protein_grams,
                    carb_target=macros.carb_grams,
                    fat_target=macros.fat_grams,
                    diet_type=None,
                    allergies=None,
                    calorie_tolerance=macro_aware_tolerance,
                    max_attempts=250,
                )
            else:
                solver_plan = generate_meal_plan(
                    foods=candidate_foods,
                    calorie_target=base_meal_calorie_target,
                    max_meals=4,
                    calorie_tolerance=0.10,
                    max_attempts=150,
                    shuffle=True,
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
                user_goal=user_profile.goal.value,
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
                warnings=[*planner_macro_warnings, *supplement_result["warnings"]],
            )

            candidate_score = _score_totals(
                (
                    candidate_plan.total_calories,
                    candidate_plan.total_protein,
                    candidate_plan.total_carbs,
                    candidate_plan.total_fat,
                ),
                (
                    calorie_target,
                    macros.protein_grams,
                    macros.carb_grams,
                    macros.fat_grams,
                ),
            )
            if candidate_score < best_candidate_score:
                best_candidate_score = candidate_score
                best_candidate_plan = candidate_plan
                best_candidate_structure = structured_plan

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
            final_plan = candidate_plan.model_copy(update={"meal_plan": formatted_plan})
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

    if best_candidate_plan and best_candidate_structure:
        formatted_plan = format_meal_plan(best_candidate_structure)
        fallback_warnings = list(best_candidate_plan.warnings)
        fallback_warnings.append(
            "Returned best available plan after retries. Targets were partially unmet under current constraints."
        )
        return best_candidate_plan.model_copy(
            update={
                "meal_plan": formatted_plan,
                "warnings": fallback_warnings,
            }
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
