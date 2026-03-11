"""
Meal Planner Module

Master orchestrator that combines all nutrition engine modules to create
complete meal plans. This module integrates:
- Metabolic calculations (BMR, TDEE, calorie targets)
- Macro split calculations
- Meal selection and constraint solving
- Food dataset loading

For use with FastAPI applications.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException

# Import all required modules
from utils.helpers import load_food_dataset
from services.nutrition_engine.metabolic_calculator import (
    calculate_bmr,
    calculate_tdee,
    adjust_for_goal,
    calculate_complete_metabolic_profile,
    Sex,
    ActivityLevel,
    FitnessGoal
)
from services.nutrition_engine.macro_split import (
    calculate_macros,
    MacroSplit
)
from services.nutrition_engine.constraint_solver import (
    generate_meal_plan,
    generate_structured_meal_plan,
    generate_macro_aware_meal_plan,
    filter_by_diet,
    filter_by_allergies,
    validate_meal_plan,
    MealPlan
)


class UserProfile(BaseModel):
    """User profile model for meal plan generation."""
    age: int = Field(..., ge=15, le=100, description="Age in years")
    weight: float = Field(..., ge=30, le=300, description="Weight in kilograms")
    height: float = Field(..., ge=100, le=250, description="Height in centimeters")
    sex: Sex = Field(..., description="Biological sex (male/female)")
    activity_level: ActivityLevel = Field(..., description="Physical activity level")
    goal: FitnessGoal = Field(..., description="Fitness goal")
    diet_type: Optional[str] = Field(None, description="Diet preference: 'veg' (vegetarian), 'non_veg' (non-vegetarian), or 'vegan'")
    allergies: Optional[List[str]] = Field(default_factory=list, description="List of allergens to avoid")
    
    @validator('weight')
    def validate_weight(cls, v):
        if v < 30 or v > 300:
            raise ValueError("Weight must be between 30 and 300 kg")
        return v
    
    @validator('height')
    def validate_height(cls, v):
        if v < 100 or v > 250:
            raise ValueError("Height must be between 100 and 250 cm")
        return v


class MealItem(BaseModel):
    """Individual meal item in the meal plan."""
    name: str = Field(..., description="Recipe name")
    calories: float = Field(..., description="Calories (kcal)")
    protein: float = Field(..., description="Protein (g)")
    carbohydrates: float = Field(..., description="Carbohydrates (g)")
    fat: float = Field(..., description="Fat (g)")
    ingredients: str = Field(..., description="Comma-separated ingredients")
    instructions: str = Field(..., description="Cooking instructions")
    diet_type: str = Field(..., description="Diet type classification")


class CompleteMealPlan(BaseModel):
    """Complete meal plan response with all nutritional information."""
    # User info
    user_profile: Dict[str, Any] = Field(..., description="User profile used for generation")
    
    # Metabolic calculations
    bmr: float = Field(..., description="Basal Metabolic Rate (kcal/day)")
    tdee: float = Field(..., description="Total Daily Energy Expenditure (kcal/day)")
    calorie_target: float = Field(..., description="Target daily calories")
    
    # Macro targets
    macros: Dict[str, float] = Field(..., description="Macro targets (protein, carbs, fat in grams)")
    macro_percentages: Dict[str, float] = Field(..., description="Macro percentages")
    
    # Meal plan
    meals: List[MealItem] = Field(..., description="List of selected meals")
    meal_count: int = Field(..., description="Number of meals in plan")
    
    # Actual totals from selected meals
    total_calories: float = Field(..., description="Total calories from meals")
    total_protein: float = Field(..., description="Total protein from meals (g)")
    total_carbs: float = Field(..., description="Total carbohydrates from meals (g)")
    total_fat: float = Field(..., description="Total fat from meals (g)")
    
    # Accuracy metrics
    calorie_accuracy: float = Field(..., description="How close to target (percentage)")
    
    # Metadata
    goal: str = Field(..., description="Fitness goal")
    activity_level: str = Field(..., description="Activity level")


def create_meal_plan(user_profile: UserProfile) -> CompleteMealPlan:
    """
    Create a complete meal plan for a user based on their profile.
    
    This is the master orchestrator function that combines all nutrition
    engine modules to generate a personalized meal plan with exactly 4 meals:
    - Breakfast: 25% of daily calories
    - Lunch: 35% of daily calories
    - Dinner: 30% of daily calories
    - Snack: 10% of daily calories
    
    Uses GREEDY MACRO-AWARE OPTIMIZATION:
    - Keeps calorie deviation within ±10%
    - Tracks and optimizes macro totals (protein, carbs, fat)
    - Scores meals based on how well they fit remaining targets
    - Selects meals that minimize macro deviation
    - Avoids simple random selection
    
    Workflow:
    1. Load food dataset
    2. Calculate BMR (Basal Metabolic Rate)
    3. Calculate TDEE (Total Daily Energy Expenditure)
    4. Adjust for fitness goal
    5. Calculate macro targets based on goal and weight
    6. Filter meals by diet preferences and allergies
    7. Generate optimized 4-meal plan using greedy algorithm
    8. Format and return structured response
    
    Args:
        user_profile (UserProfile): User's profile including age, weight, height,
                                    sex, activity level, goal, preferences
    
    Returns:
        CompleteMealPlan: Complete meal plan with 4 meals and nutritional breakdown
        
    Raises:
        HTTPException: If meal plan generation fails
        
    Example:
        >>> profile = UserProfile(
        ...     age=25, weight=70, height=175, sex=Sex.MALE,
        ...     activity_level=ActivityLevel.MODERATELY_ACTIVE,
        ...     goal=FitnessGoal.MUSCLE_GAIN,
        ...     diet_type="veg",  # Options: "veg", "non_veg", "vegan"
        ...     allergies=["milk"]
        ... )
        >>> plan = create_meal_plan(profile)
        >>> print(f"Generated {plan.meal_count} meals for {plan.calorie_target} kcal/day")
        >>> # Returns: Breakfast (25%), Lunch (35%), Dinner (30%), Snack (10%)
        >>> # With optimized macros close to targets
    """
    try:
        # Step 1: Load food dataset
        foods = load_food_dataset()
        
        # Step 2: Calculate BMR
        bmr = calculate_bmr(
            age=user_profile.age,
            weight=user_profile.weight,
            height=user_profile.height,
            sex=user_profile.sex
        )
        
        # Step 3: Calculate TDEE
        tdee = calculate_tdee(
            bmr=bmr,
            activity_level=user_profile.activity_level
        )
        
        # Step 4: Adjust for goal
        calorie_target = adjust_for_goal(
            tdee=tdee,
            goal=user_profile.goal,
            sex=user_profile.sex
        )
        
        # Step 5: Calculate macro targets
        macros = calculate_macros(
            calories=calorie_target,
            goal=user_profile.goal,
            weight_kg=user_profile.weight
        )
        
        # Step 6 & 7: Generate macro-aware meal plan using greedy optimization
        # - Fixed 4-meal distribution: Breakfast 25%, Lunch 35%, Dinner 30%, Snack 10%
        # - Keeps calorie deviation within ±10%
        # - Optimizes for macro targets (protein, carbs, fat)
        # - Uses greedy algorithm to select meals that minimize macro deviation
        meal_plan = generate_macro_aware_meal_plan(
            foods=foods,
            calorie_target=calorie_target,
            protein_target=macros.protein_grams,
            carb_target=macros.carb_grams,
            fat_target=macros.fat_grams,
            diet_type=user_profile.diet_type,
            allergies=user_profile.allergies or [],
            calorie_tolerance=0.10,  # ±10% calorie deviation
            max_attempts=100  # Optimization attempts for best macro balance
        )
        
        # Step 8: Format meals into response structure
        formatted_meals = []
        for meal in meal_plan.meals:
            formatted_meals.append(MealItem(
                name=meal.get('RecipeName', 'Unknown'),
                calories=round(meal.get('Calories', 0), 2),
                protein=round(meal.get('Protein', 0), 2),
                carbohydrates=round(meal.get('Carbohydrates', 0), 2),
                fat=round(meal.get('Fat', 0), 2),
                ingredients=meal.get('Ingredients', ''),
                instructions=meal.get('Instructions', ''),
                diet_type=meal.get('DietType', 'Unknown')
            ))
        
        # Calculate accuracy
        if calorie_target == 0:
            calorie_accuracy = 100.0 if meal_plan.total_calories == 0 else 0.0
        else:
            calorie_accuracy = 100 - abs((meal_plan.total_calories - calorie_target) / calorie_target * 100)
        
        # Create complete response
        complete_plan = CompleteMealPlan(
            user_profile={
                'age': user_profile.age,
                'weight': user_profile.weight,
                'height': user_profile.height,
                'sex': user_profile.sex.value,
                'activity_level': user_profile.activity_level.value,
                'goal': user_profile.goal.value,
                'diet_type': user_profile.diet_type,
                'allergies': user_profile.allergies
            },
            bmr=round(bmr, 2),
            tdee=round(tdee, 2),
            calorie_target=round(calorie_target, 2),
            macros={
                'protein': macros.protein_grams,
                'carbohydrates': macros.carb_grams,
                'fat': macros.fat_grams
            },
            macro_percentages={
                'protein': macros.protein_percentage,
                'carbohydrates': macros.carb_percentage,
                'fat': macros.fat_percentage
            },
            meals=formatted_meals,
            meal_count=meal_plan.meal_count,
            total_calories=meal_plan.total_calories,
            total_protein=meal_plan.total_protein,
            total_carbs=meal_plan.total_carbs,
            total_fat=meal_plan.total_fat,
            calorie_accuracy=round(calorie_accuracy, 2),
            goal=user_profile.goal.value,
            activity_level=user_profile.activity_level.value
        )
        
        return complete_plan
        
    except HTTPException:
        # Re-raise HTTP exceptions from underlying modules
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating meal plan: {str(e)}"
        )


def get_meal_plan_summary(meal_plan: CompleteMealPlan) -> Dict[str, Any]:
    """
    Get a summary of the meal plan for quick display.
    
    Args:
        meal_plan (CompleteMealPlan): Complete meal plan
    
    Returns:
        Dict[str, Any]: Summary with key metrics
        
    Example:
        >>> summary = get_meal_plan_summary(plan)
        >>> print(f"Total: {summary['total_calories']} kcal")
    """
    return {
        'meal_count': meal_plan.meal_count,
        'total_calories': meal_plan.total_calories,
        'calorie_target': meal_plan.calorie_target,
        'accuracy': f"{meal_plan.calorie_accuracy}%",
        'macros': meal_plan.macros,
        'goal': meal_plan.goal,
        'meal_names': [meal.name for meal in meal_plan.meals]
    }


def validate_user_profile(profile_data: Dict[str, Any]) -> UserProfile:
    """
    Validate and create UserProfile from raw data.
    
    Useful for API endpoints that receive JSON data.
    
    Args:
        profile_data (Dict[str, Any]): Raw profile data
    
    Returns:
        UserProfile: Validated user profile
        
    Raises:
        HTTPException: If validation fails
        
    Example:
        >>> data = {
        ...     "age": 25, "weight": 70, "height": 175,
        ...     "sex": "male", "activity_level": "moderately_active",
        ...     "goal": "muscle_gain"
        ... }
        >>> profile = validate_user_profile(data)
    """
    try:
        return UserProfile(**profile_data)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid user profile: {str(e)}"
        )


def regenerate_meal_plan_with_changes(
    user_profile: UserProfile,
    exclude_meals: Optional[List[str]] = None,
    prefer_high_protein: bool = False
) -> CompleteMealPlan:
    """
    Regenerate meal plan with modifications.
    
    Useful for when users want to replace certain meals or adjust preferences.
    
    Args:
        user_profile (UserProfile): User's profile
        exclude_meals (Optional[List[str]]): Recipe names to exclude
        prefer_high_protein (bool): Prioritize high-protein meals
    
    Returns:
        CompleteMealPlan: New meal plan with modifications
        
    Example:
        >>> # User doesn't like one meal, regenerate without it
        >>> new_plan = regenerate_meal_plan_with_changes(
        ...     profile, exclude_meals=["Paneer Tikka"]
        ... )
    """
    try:
        # Load dataset
        foods = load_food_dataset()
        
        # Remove excluded meals
        if exclude_meals:
            foods = [
                food for food in foods
                if food.get('RecipeName', '') not in exclude_meals
            ]
        
        # Sort for preferences if needed
        if prefer_high_protein:
            foods.sort(
                key=lambda x: x.get('Protein', 0) / max(x.get('Calories', 1), 1),
                reverse=True
            )
        
        # Calculate calorie target
        bmr = calculate_bmr(
            user_profile.age, user_profile.weight,
            user_profile.height, user_profile.sex
        )
        tdee = calculate_tdee(bmr, user_profile.activity_level)
        calorie_target = adjust_for_goal(tdee, user_profile.goal, user_profile.sex)
        
        # Calculate macro targets
        macros = calculate_macros(
            calories=calorie_target,
            goal=user_profile.goal,
            weight_kg=user_profile.weight
        )
        
        # Generate new macro-aware meal plan
        # Note: prefer_high_protein sorting is already done on foods list
        meal_plan = generate_macro_aware_meal_plan(
            foods=foods,
            calorie_target=calorie_target,
            protein_target=macros.protein_grams,
            carb_target=macros.carb_grams,
            fat_target=macros.fat_grams,
            diet_type=user_profile.diet_type,
            allergies=user_profile.allergies or [],
            calorie_tolerance=0.10,
            max_attempts=100
        )
        
        # Format meals into response structure
        formatted_meals = []
        for meal in meal_plan.meals:
            formatted_meals.append(MealItem(
                name=meal.get('RecipeName', 'Unknown'),
                calories=round(meal.get('Calories', 0), 2),
                protein=round(meal.get('Protein', 0), 2),
                carbohydrates=round(meal.get('Carbohydrates', 0), 2),
                fat=round(meal.get('Fat', 0), 2),
                ingredients=meal.get('Ingredients', ''),
                instructions=meal.get('Instructions', ''),
                diet_type=meal.get('DietType', 'Unknown')
            ))
        
        # Calculate accuracy
        if calorie_target == 0:
            calorie_accuracy = 100.0 if meal_plan.total_calories == 0 else 0.0
        else:
            calorie_accuracy = 100 - abs((meal_plan.total_calories - calorie_target) / calorie_target * 100)
        
        # Create complete response
        complete_plan = CompleteMealPlan(
            user_profile={
                'age': user_profile.age,
                'weight': user_profile.weight,
                'height': user_profile.height,
                'sex': user_profile.sex.value,
                'activity_level': user_profile.activity_level.value,
                'goal': user_profile.goal.value,
                'diet_type': user_profile.diet_type,
                'allergies': user_profile.allergies
            },
            bmr=round(bmr, 2),
            tdee=round(tdee, 2),
            calorie_target=round(calorie_target, 2),
            macros={
                'protein': macros.protein_grams,
                'carbohydrates': macros.carb_grams,
                'fat': macros.fat_grams
            },
            macro_percentages={
                'protein': macros.protein_percentage,
                'carbohydrates': macros.carb_percentage,
                'fat': macros.fat_percentage
            },
            meals=formatted_meals,
            meal_count=meal_plan.meal_count,
            total_calories=meal_plan.total_calories,
            total_protein=meal_plan.total_protein,
            total_carbs=meal_plan.total_carbs,
            total_fat=meal_plan.total_fat,
            calorie_accuracy=round(calorie_accuracy, 2),
            goal=user_profile.goal.value,
            activity_level=user_profile.activity_level.value
        )
        
        return complete_plan
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerating meal plan: {str(e)}"
        )


def get_daily_meal_distribution(
    calorie_target: float,
    meal_count: int = 4
) -> Dict[str, Dict[str, float]]:
    """
    Get recommended calorie distribution across meals.
    
    Helps users understand how to distribute calories throughout the day.
    
    Args:
        calorie_target (float): Total daily calories
        meal_count (int): Number of meals (default 4)
    
    Returns:
        Dict[str, Dict[str, float]]: Meal type -> calorie range
        
    Example:
        >>> distribution = get_daily_meal_distribution(2000, 3)
        >>> print(distribution)
        {
            'breakfast': {'min': 500, 'max': 600},
            'lunch': {'min': 700, 'max': 800},
            'dinner': {'min': 600, 'max': 700}
        }
    """
    if meal_count == 3:
        return {
            'breakfast': {'min': calorie_target * 0.25, 'max': calorie_target * 0.30},
            'lunch': {'min': calorie_target * 0.35, 'max': calorie_target * 0.40},
            'dinner': {'min': calorie_target * 0.30, 'max': calorie_target * 0.35}
        }
    elif meal_count == 4:
        return {
            'breakfast': {'min': calorie_target * 0.20, 'max': calorie_target * 0.25},
            'lunch': {'min': calorie_target * 0.30, 'max': calorie_target * 0.35},
            'snack': {'min': calorie_target * 0.10, 'max': calorie_target * 0.15},
            'dinner': {'min': calorie_target * 0.30, 'max': calorie_target * 0.35}
        }
    elif meal_count == 5:
        return {
            'breakfast': {'min': calorie_target * 0.20, 'max': calorie_target * 0.25},
            'morning_snack': {'min': calorie_target * 0.08, 'max': calorie_target * 0.12},
            'lunch': {'min': calorie_target * 0.30, 'max': calorie_target * 0.35},
            'evening_snack': {'min': calorie_target * 0.08, 'max': calorie_target * 0.12},
            'dinner': {'min': calorie_target * 0.25, 'max': calorie_target * 0.30}
        }
    else:
        # Equal distribution
        per_meal = calorie_target / meal_count
        return {
            f'meal_{i+1}': {'min': per_meal * 0.8, 'max': per_meal * 1.2}
            for i in range(meal_count)
        }


def compare_plan_to_targets(meal_plan: CompleteMealPlan) -> Dict[str, Any]:
    """
    Compare actual meal plan totals to targets.
    
    Provides detailed comparison of how well the meal plan meets targets.
    
    Args:
        meal_plan (CompleteMealPlan): Complete meal plan
    
    Returns:
        Dict[str, Any]: Comparison metrics
        
    Example:
        >>> comparison = compare_plan_to_targets(plan)
        >>> print(f"Protein: {comparison['protein']['actual']}g vs {comparison['protein']['target']}g")
    """
    return {
        'calories': {
            'target': meal_plan.calorie_target,
            'actual': meal_plan.total_calories,
            'difference': meal_plan.total_calories - meal_plan.calorie_target,
            'percentage': round((meal_plan.total_calories / meal_plan.calorie_target) * 100, 2) if meal_plan.calorie_target > 0 else 0
        },
        'protein': {
            'target': meal_plan.macros['protein'],
            'actual': meal_plan.total_protein,
            'difference': meal_plan.total_protein - meal_plan.macros['protein'],
            'percentage': round((meal_plan.total_protein / meal_plan.macros['protein']) * 100, 2) if meal_plan.macros['protein'] > 0 else 0
        },
        'carbohydrates': {
            'target': meal_plan.macros['carbohydrates'],
            'actual': meal_plan.total_carbs,
            'difference': meal_plan.total_carbs - meal_plan.macros['carbohydrates'],
            'percentage': round((meal_plan.total_carbs / meal_plan.macros['carbohydrates']) * 100, 2) if meal_plan.macros['carbohydrates'] > 0 else 0
        },
        'fat': {
            'target': meal_plan.macros['fat'],
            'actual': meal_plan.total_fat,
            'difference': meal_plan.total_fat - meal_plan.macros['fat'],
            'percentage': round((meal_plan.total_fat / meal_plan.macros['fat']) * 100, 2) if meal_plan.macros['fat'] > 0 else 0
        },
        'overall_accuracy': meal_plan.calorie_accuracy
    }