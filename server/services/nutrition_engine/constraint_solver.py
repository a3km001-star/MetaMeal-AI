"""
Constraint Solver Module

Core optimization engine for meal selection and planning.
This module handles:
- Filtering foods by diet type and allergies
- Selecting meals that meet calorie and macro targets
- Ensuring variety and balanced nutrition
- Optimizing meal distribution across breakfast, lunch, dinner

For use with FastAPI applications.
"""

import random
from typing import List, Dict, Optional, Tuple, Set
from pydantic import BaseModel, Field
from fastapi import HTTPException


class MealPlan(BaseModel):
    """Response model for generated meal plan."""
    meals: List[Dict] = Field(..., description="List of selected meals")
    total_calories: float = Field(..., description="Total calories in meal plan")
    total_protein: float = Field(..., description="Total protein (g)")
    total_carbs: float = Field(..., description="Total carbohydrates (g)")
    total_fat: float = Field(..., description="Total fat (g)")
    target_calories: float = Field(..., description="Target calories")
    calorie_deviation: float = Field(..., description="Deviation from target (%)")
    meal_count: int = Field(..., description="Number of meals selected")


class MealConstraints(BaseModel):
    """Constraints for meal selection."""
    calorie_target: float = Field(..., gt=0, description="Target daily calories")
    diet_type: Optional[str] = Field(None, description="Diet type filter (e.g., 'Vegetarian')")
    allergies: Optional[List[str]] = Field(default_factory=list, description="List of allergens to avoid")
    max_meals: int = Field(5, ge=1, le=10, description="Maximum number of meals")
    calorie_tolerance: float = Field(0.10, ge=0.01, le=0.30, description="Acceptable calorie deviation (default 10%)")


def filter_by_diet(foods: List[Dict], diet_type: Optional[str] = None) -> List[Dict]:
    """
    Filter foods based on diet type preference.
    
    Args:
        foods (List[Dict]): List of food items from dataset
        diet_type (Optional[str]): Diet type filter (e.g., 'Vegetarian', 'Non-Vegetarian')
                                    If None, returns all foods
    
    Returns:
        List[Dict]: Filtered list of foods matching diet type
        
    Example:
        >>> foods = load_food_dataset()
        >>> veg_foods = filter_by_diet(foods, "Vegetarian")
        >>> print(f"Found {len(veg_foods)} vegetarian recipes")
    """
    # If no diet type specified, return all foods
    if not diet_type or diet_type.lower() == "any" or diet_type.lower() == "unknown":
        return foods
    
    # Filter by diet type (case-insensitive)
    filtered = [
        food for food in foods
        if food.get('DietType', '').lower() == diet_type.lower()
    ]
    
    return filtered


def filter_by_allergies(
    foods: List[Dict],
    allergies: Optional[List[str]] = None
) -> List[Dict]:
    """
    Filter out foods containing allergens.
    
    Checks ingredients field for presence of allergen keywords.
    
    Args:
        foods (List[Dict]): List of food items from dataset
        allergies (Optional[List[str]]): List of allergen keywords to avoid
                                         (e.g., ["milk", "nuts", "eggs"])
    
    Returns:
        List[Dict]: Filtered list of foods without allergens
        
    Example:
        >>> foods = load_food_dataset()
        >>> safe_foods = filter_by_allergies(foods, ["milk", "eggs"])
        >>> print(f"Found {len(safe_foods)} recipes without milk or eggs")
    """
    # If no allergies specified, return all foods
    if not allergies or len(allergies) == 0:
        return foods
    
    # Convert allergies to lowercase for case-insensitive matching
    allergens_lower = [allergen.lower() for allergen in allergies]
    
    # Filter out foods containing any allergen
    filtered = []
    for food in foods:
        ingredients = food.get('Ingredients', '').lower()
        
        # Check if any allergen is in ingredients
        has_allergen = any(allergen in ingredients for allergen in allergens_lower)
        
        if not has_allergen:
            filtered.append(food)
    
    return filtered


def get_meals_by_calorie_range(
    foods: List[Dict],
    min_calories: float,
    max_calories: float
) -> List[Dict]:
    """
    Get meals within a specific calorie range.
    
    Useful for finding meals that fit specific meal types (breakfast, lunch, dinner).
    
    Args:
        foods (List[Dict]): List of food items
        min_calories (float): Minimum calories
        max_calories (float): Maximum calories
    
    Returns:
        List[Dict]: Meals within the calorie range
        
    Example:
        >>> # Find breakfast options (300-500 calories)
        >>> breakfast_options = get_meals_by_calorie_range(foods, 300, 500)
    """
    return [
        food for food in foods
        if min_calories <= food.get('Calories', 0) <= max_calories
    ]


def split_calories_by_meal_type(
    total_calories: float,
    meal_count: int = 3
) -> Dict[str, Tuple[float, float]]:
    """
    Split daily calories into meal types with calorie ranges.
    
    Default distribution:
    - Breakfast: 25-30% of daily calories
    - Lunch: 35-40% of daily calories 
    - Dinner: 30-35% of daily calories
    - Snacks: 10-15% of daily calories (if 4+ meals)
    
    Args:
        total_calories (float): Total daily calorie target
        meal_count (int): Number of meals per day (default 3)
    
    Returns:
        Dict[str, Tuple[float, float]]: Meal type -> (min_calories, max_calories)
        
    Example:
        >>> ranges = split_calories_by_meal_type(2000, 3)
        >>> print(ranges)
        {'breakfast': (500, 600), 'lunch': (700, 800), 'dinner': (600, 700)}
    """
    if meal_count == 3:
        return {
            'breakfast': (total_calories * 0.25, total_calories * 0.30),
            'lunch': (total_calories * 0.35, total_calories * 0.40),
            'dinner': (total_calories * 0.30, total_calories * 0.35)
        }
    elif meal_count == 4:
        return {
            'breakfast': (total_calories * 0.20, total_calories * 0.25),
            'lunch': (total_calories * 0.30, total_calories * 0.35),
            'snack': (total_calories * 0.10, total_calories * 0.15),
            'dinner': (total_calories * 0.30, total_calories * 0.35)
        }
    elif meal_count == 5:
        return {
            'breakfast': (total_calories * 0.20, total_calories * 0.25),
            'morning_snack': (total_calories * 0.08, total_calories * 0.12),
            'lunch': (total_calories * 0.30, total_calories * 0.35),
            'evening_snack': (total_calories * 0.08, total_calories * 0.12),
            'dinner': (total_calories * 0.25, total_calories * 0.30)
        }
    else:
        # Equal distribution for other meal counts
        per_meal = total_calories / meal_count
        meal_range = (per_meal * 0.8, per_meal * 1.2)
        return {f'meal_{i+1}': meal_range for i in range(meal_count)}


def ensure_variety(
    selected_meals: List[Dict],
    candidate: Dict,
    max_same_ingredients: int = 3
) -> bool:
    """
    Check if adding a candidate meal maintains variety.
    
    Prevents selecting meals with too many similar ingredients.
    
    Args:
        selected_meals (List[Dict]): Already selected meals
        candidate (Dict): Candidate meal to check
        max_same_ingredients (int): Max overlapping ingredients allowed
    
    Returns:
        bool: True if meal adds variety, False if too similar
        
    Example:
        >>> selected = [meal1, meal2]
        >>> if ensure_variety(selected, meal3):
        >>>     selected.append(meal3)
    """
    if not selected_meals:
        return True
    
    # Get candidate ingredients
    candidate_ingredients = set(
        candidate.get('Ingredients', '').lower().split(',')
    )
    
    # Check against each selected meal
    for meal in selected_meals:
        meal_ingredients = set(
            meal.get('Ingredients', '').lower().split(',')
        )
        
        # Count overlapping ingredients
        overlap = len(candidate_ingredients.intersection(meal_ingredients))
        
        # If too much overlap, reject
        if overlap > max_same_ingredients:
            return False
    
    return True


def calculate_macro_totals(meals: List[Dict]) -> Tuple[float, float, float, float]:
    """
    Calculate total calories and macros from selected meals.
    
    Args:
        meals (List[Dict]): List of selected meals
    
    Returns:
        Tuple[float, float, float, float]: (calories, protein, carbs, fat)
        
    Example:
        >>> total_cal, total_protein, total_carbs, total_fat = calculate_macro_totals(meals)
    """
    total_calories = sum(meal.get('Calories', 0) for meal in meals)
    total_protein = sum(meal.get('Protein', 0) for meal in meals)
    total_carbs = sum(meal.get('Carbohydrates', 0) for meal in meals)
    total_fat = sum(meal.get('Fat', 0) for meal in meals)
    
    return total_calories, total_protein, total_carbs, total_fat


def check_calorie_target(
    current_calories: float,
    target_calories: float,
    tolerance: float = 0.10
) -> bool:
    """
    Check if current calories are within acceptable range of target.
    
    Args:
        current_calories (float): Current total calories
        target_calories (float): Target calories
        tolerance (float): Acceptable deviation (default 10%)
    
    Returns:
        bool: True if within tolerance, False otherwise
        
    Example:
        >>> if check_calorie_target(1950, 2000, 0.10):
        >>>     print("Within 10% of target")
    """
    lower_bound = target_calories * (1 - tolerance)
    upper_bound = target_calories * (1 + tolerance)
    
    return lower_bound <= current_calories <= upper_bound


def generate_meal_plan(
    foods: List[Dict],
    calorie_target: float,
    diet_type: Optional[str] = None,
    allergies: Optional[List[str]] = None,
    max_meals: int = 5,
    calorie_tolerance: float = 0.10,
    max_attempts: int = 100
) -> MealPlan:
    """
    Generate a meal plan that meets calorie target and constraints.
    
    Algorithm:
    1. Filter foods by diet type and allergies
    2. Randomly select meals
    3. Keep adding meals until calorie target is reached
    4. Ensure variety (no repeated meals, diverse ingredients)
    5. Validate total calories within tolerance
    
    Args:
        foods (List[Dict]): Food dataset (from load_food_dataset())
        calorie_target (float): Target daily calories
        diet_type (Optional[str]): Diet type filter
        allergies (Optional[List[str]]): List of allergens to avoid
        max_meals (int): Maximum number of meals (default 5)
        calorie_tolerance (float): Acceptable deviation (default 10%)
        max_attempts (int): Maximum attempts to generate valid plan
    
    Returns:
        MealPlan: Generated meal plan with nutritional breakdown
        
    Raises:
        HTTPException: If unable to generate valid meal plan
        
    Example:
        >>> foods = load_food_dataset()
        >>> plan = generate_meal_plan(
        ...     foods=foods,
        ...     calorie_target=2000,
        ...     diet_type="Vegetarian",
        ...     allergies=["milk"],
        ...     max_meals=4
        ... )
        >>> print(f"Generated plan with {plan.meal_count} meals")
    """
    try:
        # Validate inputs
        if calorie_target <= 0:
            raise ValueError("Calorie target must be positive")
        if calorie_target < 800 or calorie_target > 6000:
            raise ValueError("Calorie target must be between 800 and 6000")
        if not foods or len(foods) == 0:
            raise ValueError("Food dataset is empty")
        
        # Step 1: Apply filters
        filtered_foods = filter_by_diet(foods, diet_type)
        filtered_foods = filter_by_allergies(filtered_foods, allergies)
        
        if not filtered_foods:
            raise ValueError(f"No foods available after applying filters (diet: {diet_type}, allergies: {allergies})")
        
        # Calculate target calories per meal (helps with meal selection)
        avg_calories_per_meal = calorie_target / max_meals
        
        # Step 2: Try to generate valid meal plan
        best_plan = None
        best_deviation = float('inf')
        
        for attempt in range(max_attempts):
            selected_meals = []
            used_recipes = set()  # Track used recipe names to avoid duplicates
            current_calories = 0.0
            remaining_target = calorie_target
            meals_remaining = max_meals
            
            # Make a copy of available foods for this attempt
            available_foods = filtered_foods.copy()
            random.shuffle(available_foods)
            
            # Step 3: Intelligently select meals to reach target
            for food in available_foods:
                # Stop if we've reached max meals
                if len(selected_meals) >= max_meals:
                    break
                
                # Skip if recipe already used
                recipe_name = food.get('RecipeName', '')
                if recipe_name in used_recipes:
                    continue
                
                food_calories = food.get('Calories', 0)
                
                # Calculate how much we still need
                calories_needed = calorie_target - current_calories
                avg_needed_per_remaining_meal = calories_needed / max(meals_remaining, 1)
                
                # Decision logic: Should we add this meal?
                should_add = False
                
                if len(selected_meals) == 0:
                    # Always add first meal if reasonable size
                    should_add = food_calories <= calorie_target * 0.5
                elif meals_remaining == 1:
                    # Last meal slot - try to get close to remaining target
                    should_add = abs(food_calories - calories_needed) <= calorie_target * 0.20
                else:
                    # Middle meals - aim for average per meal, with flexibility
                    min_acceptable = avg_needed_per_remaining_meal * 0.5
                    max_acceptable = avg_needed_per_remaining_meal * 1.8
                    should_add = min_acceptable <= food_calories <= max_acceptable
                
                # Add meal if it passes criteria
                if should_add:
                    # Check variety
                    if ensure_variety(selected_meals, food, max_same_ingredients=5):
                        selected_meals.append(food)
                        used_recipes.add(recipe_name)
                        current_calories += food_calories
                        meals_remaining -= 1
                        
                        # Early exit if we're within tolerance
                        if check_calorie_target(current_calories, calorie_target, calorie_tolerance):
                            break
            
            # Calculate totals
            total_calories, total_protein, total_carbs, total_fat = calculate_macro_totals(selected_meals)
            
            # Calculate deviation
            if total_calories > 0:
                deviation = abs(total_calories - calorie_target) / calorie_target
            else:
                deviation = 1.0
            
            # Check if this plan is valid and better than previous best
            is_valid = check_calorie_target(total_calories, calorie_target, calorie_tolerance)
            
            if is_valid:
                if deviation < best_deviation:
                    best_deviation = deviation
                    best_plan = MealPlan(
                        meals=selected_meals,
                        total_calories=round(total_calories, 2),
                        total_protein=round(total_protein, 2),
                        total_carbs=round(total_carbs, 2),
                        total_fat=round(total_fat, 2),
                        target_calories=calorie_target,
                        calorie_deviation=round(deviation * 100, 2),
                        meal_count=len(selected_meals)
                    )
                    
                    # If deviation is very small, we can stop early
                    if deviation < 0.02:  # Less than 2% deviation
                        break
            else:
                # Even if not valid, save if it's the closest we've gotten
                if deviation < best_deviation and selected_meals:
                    # Relaxed acceptance for "best attempt"
                    if deviation < calorie_tolerance * 1.5:  # Within 15% for 10% tolerance
                        best_deviation = deviation
                        best_plan = MealPlan(
                            meals=selected_meals,
                            total_calories=round(total_calories, 2),
                            total_protein=round(total_protein, 2),
                            total_carbs=round(total_carbs, 2),
                            total_fat=round(total_fat, 2),
                            target_calories=calorie_target,
                            calorie_deviation=round(deviation * 100, 2),
                            meal_count=len(selected_meals)
                        )
        
        # Return best plan found
        if best_plan:
            return best_plan
        else:
            raise ValueError(
                f"Unable to generate meal plan within {calorie_tolerance*100}% tolerance "
                f"after {max_attempts} attempts. Try increasing tolerance or max_meals parameter."
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating meal plan: {str(e)}"
        )


def optimize_meal_selection(
    foods: List[Dict],
    calorie_target: float,
    protein_target: Optional[float] = None,
    diet_type: Optional[str] = None,
    allergies: Optional[List[str]] = None,
    prefer_high_protein: bool = False,
    prefer_low_fat: bool = False
) -> MealPlan:
    """
    Generate optimized meal plan with macro targeting.
    
    More advanced version of generate_meal_plan that also considers
    protein and fat targets, not just calories.
    
    Args:
        foods (List[Dict]): Food dataset
        calorie_target (float): Target daily calories
        protein_target (Optional[float]): Target protein in grams
        diet_type (Optional[str]): Diet type filter
        allergies (Optional[List[str]]): Allergens to avoid
        prefer_high_protein (bool): Prioritize high-protein foods
        prefer_low_fat (bool): Prioritize low-fat foods
    
    Returns:
        MealPlan: Optimized meal plan
        
    Example:
        >>> plan = optimize_meal_selection(
        ...     foods=foods,
        ...     calorie_target=2000,
        ...     protein_target=150,
        ...     prefer_high_protein=True
        ... )
    """
    # Filter foods
    filtered_foods = filter_by_diet(foods, diet_type)
    filtered_foods = filter_by_allergies(filtered_foods, allergies)
    
    # Sort foods based on preferences
    if prefer_high_protein:
        # Sort by protein-to-calorie ratio (descending)
        filtered_foods.sort(
            key=lambda x: x.get('Protein', 0) / max(x.get('Calories', 1), 1),
            reverse=True
        )
    elif prefer_low_fat:
        # Sort by fat-to-calorie ratio (ascending)
        filtered_foods.sort(
            key=lambda x: x.get('Fat', 0) / max(x.get('Calories', 1), 1)
        )
    
    # Generate meal plan using the optimized order
    return generate_meal_plan(
        foods=filtered_foods,
        calorie_target=calorie_target,
        diet_type=diet_type,
        allergies=allergies,
        max_meals=5,
        calorie_tolerance=0.10
    )


def validate_meal_plan(
    meal_plan: MealPlan,
    calorie_target: float,
    calorie_tolerance: float = 0.10
) -> bool:
    """
    Validate that a meal plan meets requirements.
    
    Checks:
    - Calories within tolerance
    - At least one meal selected
    - No duplicate meals
    
    Args:
        meal_plan (MealPlan): Meal plan to validate
        calorie_target (float): Target calories
        calorie_tolerance (float): Acceptable deviation
    
    Returns:
        bool: True if valid, False otherwise
        
    Example:
        >>> if validate_meal_plan(plan, 2000, 0.10):
        >>>     print("Plan is valid")
    """
    # Check meal count
    if meal_plan.meal_count == 0:
        return False
    
    # Check calorie tolerance
    if not check_calorie_target(meal_plan.total_calories, calorie_target, calorie_tolerance):
        return False
    
    # Check for duplicate meals
    recipe_names = [meal.get('RecipeName', '') for meal in meal_plan.meals]
    if len(recipe_names) != len(set(recipe_names)):
        return False
    
    return True