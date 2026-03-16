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
import re
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
    
    Supports three diet types:
    - veg/vegetarian: Vegetarian foods (no meat, fish, eggs)
    - non_veg/non-vegetarian: Non-vegetarian foods (includes all foods)
    - vegan: Plant-based only (no meat, fish, eggs, dairy)
    
    Args:
        foods (List[Dict]): List of food items from dataset
        diet_type (Optional[str]): Diet type filter (veg, non_veg, vegan)
                                    If None, returns all foods
    
    Returns:
        List[Dict]: Filtered list of foods matching diet type
        
    Example:
        >>> foods = load_food_dataset()
        >>> veg_foods = filter_by_diet(foods, "veg")
        >>> print(f"Found {len(veg_foods)} vegetarian recipes")
    """
    # If no diet type specified, return all foods
    if not diet_type or diet_type.lower() in ["any", "unknown", "all"]:
        return foods
    
    # Normalize diet type input
    diet_lower = diet_type.lower().strip()
    
    # Map user input to standard values
    diet_map = {
        'veg': 'vegetarian',
        'vegetarian': 'vegetarian',
        'non_veg': 'non-vegetarian',
        'non-veg': 'non-vegetarian',
        'nonveg': 'non-vegetarian',
        'non vegetarian': 'non-vegetarian',
        'non-vegetarian': 'non-vegetarian',
        'vegan': 'vegan'
    }
    
    normalized_diet = diet_map.get(diet_lower, diet_lower)
    
    # Non-meat ingredients (for detecting vegetarian foods)
    non_veg_keywords = [
        'chicken', 'mutton', 'lamb', 'beef', 'pork', 'fish', 'prawn', 'shrimp',
        'meat', 'egg', 'crab', 'lobster', 'salmon', 'tuna', 'anchovy', 'bacon',
        'sausage', 'ham', 'turkey', 'duck', 'goat'
    ]
    
    # Dairy and animal products (for vegan detection)
    non_vegan_keywords = [
        'milk', 'curd', 'yogurt', 'yoghurt', 'cheese', 'paneer', 'cream',
        'butter', 'ghee', 'dairy', 'whey', 'casein', 'egg', 'honey'
    ] + non_veg_keywords
    
    filtered = []
    
    for food in foods:
        ingredients = food.get('Ingredients', '').lower()
        diet_type_field = food.get('DietType', 'Unknown').lower()
        
        if normalized_diet == 'vegetarian':
            # Include if explicitly marked vegetarian OR no non-veg ingredients
            if diet_type_field == 'vegetarian':
                filtered.append(food)
            elif diet_type_field == 'unknown':
                # Check ingredients
                has_non_veg = any(
                    re.search(r'\b' + re.escape(keyword) + r'\b', ingredients)
                    for keyword in non_veg_keywords
                )
                if not has_non_veg:
                    filtered.append(food)
        
        elif normalized_diet == 'non-vegetarian':
            # Include all foods (vegetarian + non-vegetarian)
            filtered.append(food)
        
        elif normalized_diet == 'vegan':
            # Exclude anything with non-vegan ingredients
            # Accept foods marked as vegan, vegetarian, or unknown, then check ingredients
            if diet_type_field in ('vegan', 'vegetarian', 'unknown'):
                # Check for dairy and animal products
                has_non_vegan = any(
                    re.search(r'\b' + re.escape(keyword) + r'\b', ingredients)
                    for keyword in non_vegan_keywords
                )
                if not has_non_vegan:
                    filtered.append(food)
    
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
    
    # Filter out foods containing any allergen using word boundary matching
    filtered = []
    for food in foods:
        ingredients = food.get('Ingredients', '').lower()
        
        # Check if any allergen is in ingredients using word boundaries
        has_allergen = False
        for allergen in allergens_lower:
            # Use word boundary regex to avoid false positives (e.g., "nut" in "nutmeg")
            pattern = r'\b' + re.escape(allergen) + r'\b'
            if re.search(pattern, ingredients):
                has_allergen = True
                break
        
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
    total_calories: float
) -> Dict[str, float]:
    """
    Split daily calories into meal types with exact calorie targets.
    
    Always returns fixed 4-meal distribution:
    - Breakfast: 25% of daily calories
    - Lunch: 35% of daily calories 
    - Dinner: 30% of daily calories
    - Snack: 10% of daily calories
    
    Args:
        total_calories (float): Total daily calorie target
    
    Returns:
        Dict[str, float]: Meal type -> target_calories
        
    Example:
        >>> targets = split_calories_by_meal_type(2000)
        >>> print(targets)
        {'breakfast': 500.0, 'lunch': 700.0, 'dinner': 600.0, 'snack': 200.0}
    """
    # Always return 4 meals with fixed distribution
    return {
        'breakfast': total_calories * 0.25,  # 25%
        'lunch': total_calories * 0.35,      # 35%
        'dinner': total_calories * 0.30,     # 30%
        'snack': total_calories * 0.10       # 10%
    }


def calculate_meal_fitness_score(
    meal: Dict,
    target_calories: float,
    target_protein: float,
    target_carbs: float,
    target_fat: float,
    current_protein: float = 0,
    current_carbs: float = 0,
    current_fat: float = 0,
    calorie_weight: float = 1.0,
    macro_weight: float = 1.5
) -> float:
    """
    Calculate fitness score for a meal based on how well it fits remaining targets.
    
    Uses greedy optimization: lower score is better.
    Score combines calorie deviation and macro deviations.
    
    Args:
        meal (Dict): Candidate meal
        target_calories (float): Remaining calorie target
        target_protein (float): Remaining protein target (g)
        target_carbs (float): Remaining carbs target (g)
        target_fat (float): Remaining fat target (g)
        current_protein (float): Current protein total (g)
        current_carbs (float): Current carbs total (g)
        current_fat (float): Current fat total (g)
        calorie_weight (float): Weight for calorie deviation
        macro_weight (float): Weight for macro deviations
    
    Returns:
        float: Fitness score (lower is better)
        
    Example:
        >>> score = calculate_meal_fitness_score(meal, 500, 40, 60, 15)
        >>> # Lower score means meal is a better fit for targets
    """
    meal_calories = meal.get('Calories', 0)
    meal_protein = meal.get('Protein', 0)
    meal_carbs = meal.get('Carbohydrates', 0)
    meal_fat = meal.get('Fat', 0)
    
    # Calculate what macros would be after adding this meal
    new_protein = current_protein + meal_protein
    new_carbs = current_carbs + meal_carbs
    new_fat = current_fat + meal_fat
    
    # Calculate remaining targets after this meal
    remaining_protein = target_protein - new_protein
    remaining_carbs = target_carbs - new_carbs
    remaining_fat = target_fat - new_fat
    
    # Calorie deviation (normalized)
    if target_calories > 0:
        calorie_deviation = abs(meal_calories - target_calories) / target_calories
    else:
        calorie_deviation = 0
    
    # Macro deviations (normalized and weighted by importance)
    protein_deviation = abs(remaining_protein) / max(target_protein, 1)
    carbs_deviation = abs(remaining_carbs) / max(target_carbs, 1)
    fat_deviation = abs(remaining_fat) / max(target_fat, 1)
    
    # Penalty for overshooting (going over target is worse than under)
    overshoot_penalty = 0
    if remaining_protein < 0:
        overshoot_penalty += abs(remaining_protein) / max(target_protein, 1) * 0.5
    if remaining_carbs < 0:
        overshoot_penalty += abs(remaining_carbs) / max(target_carbs, 1) * 0.5
    if remaining_fat < 0:
        overshoot_penalty += abs(remaining_fat) / max(target_fat, 1) * 0.5
    if meal_calories > target_calories * 1.2:
        overshoot_penalty += 1.0
    
    # Combined score (lower is better)
    macro_score = (protein_deviation + carbs_deviation + fat_deviation) / 3
    total_score = (calorie_weight * calorie_deviation) + (macro_weight * macro_score) + overshoot_penalty
    
    return total_score


def select_meal_greedy(
    available_meals: List[Dict],
    target_calories: float,
    target_protein: float,
    target_carbs: float,
    target_fat: float,
    current_protein: float = 0,
    current_carbs: float = 0,
    current_fat: float = 0,
    selected_meals: Optional[List[Dict]] = None,
    max_same_ingredients: int = 5
) -> Optional[Dict]:
    """
    Select best meal using greedy optimization based on macro-aware scoring.
    
    Args:
        available_meals (List[Dict]): Candidate meals
        target_calories (float): Remaining calorie target
        target_protein (float): Remaining protein target (g)
        target_carbs (float): Remaining carbs target (g)
        target_fat (float): Remaining fat target (g)
        current_protein (float): Current protein total (g)
        current_carbs (float): Current carbs total (g)
        current_fat (float): Current fat total (g)
        selected_meals (Optional[List[Dict]]): Already selected meals
        max_same_ingredients (int): Max overlapping ingredients
    
    Returns:
        Optional[Dict]: Best meal or None if none available
        
    Example:
        >>> best = select_meal_greedy(meals, 500, 40, 60, 15)
        >>> # Returns meal that best fits remaining targets
    """
    if not available_meals:
        return None
    
    selected_meals = selected_meals or []
    best_meal = None
    best_score = float('inf')
    
    # Score all candidate meals
    for meal in available_meals:
        # Check variety constraint
        if not ensure_variety(selected_meals, meal, max_same_ingredients):
            continue
        
        # Calculate fitness score
        score = calculate_meal_fitness_score(
            meal=meal,
            target_calories=target_calories,
            target_protein=target_protein,
            target_carbs=target_carbs,
            target_fat=target_fat,
            current_protein=current_protein,
            current_carbs=current_carbs,
            current_fat=current_fat
        )
        
        # Keep track of best meal
        if score < best_score:
            best_score = score
            best_meal = meal
    
    return best_meal


def generate_macro_aware_meal_plan(
    foods: List[Dict],
    calorie_target: float,
    protein_target: float,
    carb_target: float,
    fat_target: float,
    diet_type: Optional[str] = None,
    allergies: Optional[List[str]] = None,
    calorie_tolerance: float = 0.10,
    max_attempts: int = 100
) -> MealPlan:
    """
    Generate meal plan using greedy macro-aware optimization.
    
    Uses intelligent greedy algorithm to:
    - Select 4 meals (Breakfast 25%, Lunch 35%, Dinner 30%, Snack 10%)
    - Keep calorie deviation within ±10%
    - Optimize for macro targets (protein, carbs, fat)
    - Score each meal based on how well it fits remaining targets
    - Prefer meals that reduce macro deviation
    
    Args:
        foods (List[Dict]): Food dataset
        calorie_target (float): Target daily calories
        protein_target (float): Target daily protein (g)
        carb_target (float): Target daily carbs (g)
        fat_target (float): Target daily fat (g)
        diet_type (Optional[str]): Diet type filter
        allergies (Optional[List[str]]): Allergens to avoid
        calorie_tolerance (float): Acceptable deviation (default 10%)
        max_attempts (int): Max optimization attempts
    
    Returns:
        MealPlan: Optimized 4-meal plan
        
    Raises:
        HTTPException: If unable to generate valid plan
        
    Example:
        >>> plan = generate_macro_aware_meal_plan(
        ...     foods, 2000, 150, 200, 65, "veg"
        ... )
        >>> # Returns optimized plan with macros close to targets
    """
    try:
        # Validate inputs
        if calorie_target <= 0:
            raise ValueError("Calorie target must be positive")
        if calorie_target < 800 or calorie_target > 6000:
            raise ValueError("Calorie target must be between 800 and 6000")
        if not foods or len(foods) == 0:
            raise ValueError("Food dataset is empty")
        
        # Apply filters
        filtered_foods = filter_by_diet(foods, diet_type)
        filtered_foods = filter_by_allergies(filtered_foods, allergies)
        
        if not filtered_foods:
            raise ValueError(f"No foods available after applying filters")
        
        # Get calorie targets for each meal
        meal_calorie_targets = split_calories_by_meal_type(calorie_target)
        
        # Distribute macro targets proportionally across meals
        meal_order = ['breakfast', 'lunch', 'dinner', 'snack']
        meal_percentages = {
            'breakfast': 0.25,
            'lunch': 0.35,
            'dinner': 0.30,
            'snack': 0.10
        }
        
        # Track selected meals and running totals
        selected_meals = {}
        used_recipes = set()
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_calories = 0.0
        
        best_valid_plan = None
        best_deviation = float('inf')
        
        # Try multiple times to get best plan
        for attempt in range(max_attempts):
            selected_meals = {}
            used_recipes = set()
            total_protein = 0.0
            total_carbs = 0.0
            total_fat = 0.0
            total_calories = 0.0
            
            # Select meals in order using greedy optimization
            for meal_type in meal_order:
                meal_cal_target = meal_calorie_targets[meal_type]
                meal_percentage = meal_percentages[meal_type]
                
                # Calculate remaining macro targets for this meal
                remaining_meals = len(meal_order) - len(selected_meals)
                if remaining_meals > 0:
                    # Proportional targets for this meal
                    meal_protein_target = protein_target * meal_percentage
                    meal_carb_target = carb_target * meal_percentage
                    meal_fat_target = fat_target * meal_percentage
                    
                    # Adjust based on what's already been selected
                    remaining_protein = protein_target - total_protein
                    remaining_carbs = carb_target - total_carbs
                    remaining_fat = fat_target - total_fat
                    
                    # Use adjusted targets if they're more appropriate
                    if remaining_meals > 1:
                        meal_protein_target = min(meal_protein_target * 1.3, remaining_protein * 0.8)
                        meal_carb_target = min(meal_carb_target * 1.3, remaining_carbs * 0.8)
                        meal_fat_target = min(meal_fat_target * 1.3, remaining_fat * 0.8)
                    else:
                        # Last meal - target exactly what's remaining
                        meal_protein_target = remaining_protein
                        meal_carb_target = remaining_carbs
                        meal_fat_target = remaining_fat
                else:
                    meal_protein_target = protein_target * meal_percentage
                    meal_carb_target = carb_target * meal_percentage
                    meal_fat_target = fat_target * meal_percentage
                
                # Filter meals by calorie range (with tolerance)
                min_calories = meal_cal_target * (1 - calorie_tolerance * 1.5)
                max_calories = meal_cal_target * (1 + calorie_tolerance * 1.5)
                
                candidate_meals = [
                    food for food in filtered_foods
                    if min_calories <= food.get('Calories', 0) <= max_calories
                    and food.get('RecipeName', '') not in used_recipes
                ]
                
                # If no meals in range, expand search
                if not candidate_meals:
                    candidate_meals = [
                        food for food in filtered_foods
                        if food.get('RecipeName', '') not in used_recipes
                    ]
                
                if not candidate_meals:
                    break  # No more meals available
                
                # Use greedy selection
                best_meal = select_meal_greedy(
                    available_meals=candidate_meals,
                    target_calories=meal_cal_target,
                    target_protein=meal_protein_target,
                    target_carbs=meal_carb_target,
                    target_fat=meal_fat_target,
                    current_protein=total_protein,
                    current_carbs=total_carbs,
                    current_fat=total_fat,
                    selected_meals=list(selected_meals.values())
                )
                
                # Fallback: if greedy fails, pick closest by calories
                if best_meal is None and candidate_meals:
                    candidate_meals.sort(
                        key=lambda x: abs(x.get('Calories', 0) - meal_cal_target)
                    )
                    for candidate in candidate_meals:
                        if ensure_variety(list(selected_meals.values()), candidate, 5):
                            best_meal = candidate
                            break
                    if best_meal is None:
                        best_meal = candidate_meals[0]
                
                if best_meal is None:
                    break
                
                # Add meal to plan
                selected_meals[meal_type] = best_meal
                used_recipes.add(best_meal.get('RecipeName', ''))
                total_calories += best_meal.get('Calories', 0)
                total_protein += best_meal.get('Protein', 0)
                total_carbs += best_meal.get('Carbohydrates', 0)
                total_fat += best_meal.get('Fat', 0)
            
            # Check if we got all 4 meals
            if len(selected_meals) != 4:
                continue
            
            # Calculate deviations
            cal_deviation = abs(total_calories - calorie_target) / calorie_target
            protein_deviation = abs(total_protein - protein_target) / max(protein_target, 1)
            carb_deviation = abs(total_carbs - carb_target) / max(carb_target, 1)
            fat_deviation = abs(total_fat - fat_target) / max(fat_target, 1)
            
            # Combined deviation score
            combined_deviation = cal_deviation + (protein_deviation + carb_deviation + fat_deviation) / 3
            
            # Check if within calorie tolerance
            is_valid = cal_deviation <= calorie_tolerance
            
            if is_valid and combined_deviation < best_deviation:
                best_deviation = combined_deviation
                best_valid_plan = {
                    'meals': list(selected_meals.values()),
                    'total_calories': total_calories,
                    'total_protein': total_protein,
                    'total_carbs': total_carbs,
                    'total_fat': total_fat,
                    'cal_deviation': cal_deviation
                }
                
                # If very good, stop early
                if combined_deviation < 0.05:
                    break
        
        # Return best plan found
        if best_valid_plan:
            return MealPlan(
                meals=best_valid_plan['meals'],
                total_calories=round(best_valid_plan['total_calories'], 2),
                total_protein=round(best_valid_plan['total_protein'], 2),
                total_carbs=round(best_valid_plan['total_carbs'], 2),
                total_fat=round(best_valid_plan['total_fat'], 2),
                target_calories=calorie_target,
                calorie_deviation=round(best_valid_plan['cal_deviation'] * 100, 2),
                meal_count=4
            )
        else:
            raise ValueError(
                f"Unable to generate meal plan within {calorie_tolerance*100}% tolerance. "
                f"Try adjusting filters or increasing tolerance."
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating macro-aware meal plan: {str(e)}"
        )


def generate_structured_meal_plan(
    foods: List[Dict],
    calorie_target: float,
    diet_type: Optional[str] = None,
    allergies: Optional[List[str]] = None,
    calorie_tolerance: float = 0.15,
    max_attempts: int = 200
) -> MealPlan:
    """
    Generate a meal plan with exactly 4 meals following fixed calorie distribution.
    
    Meal structure:
    - Breakfast: 25% of daily calories
    - Lunch: 35% of daily calories
    - Dinner: 30% of daily calories
    - Snack: 10% of daily calories
    
    Args:
        foods (List[Dict]): Food dataset
        calorie_target (float): Target daily calories
        diet_type (Optional[str]): Diet type filter
        allergies (Optional[List[str]]): List of allergens to avoid
        calorie_tolerance (float): Acceptable per-meal deviation (default 15%)
        max_attempts (int): Maximum attempts per meal selection
    
    Returns:
        MealPlan: Structured meal plan with exactly 4 meals
        
    Raises:
        HTTPException: If unable to generate valid meal plan
        
    Example:
        >>> plan = generate_structured_meal_plan(foods, 2000, "Vegetarian")
        >>> # Returns plan with breakfast=500, lunch=700, dinner=600, snack=200
    """
    try:
        # Validate inputs
        if calorie_target <= 0:
            raise ValueError("Calorie target must be positive")
        if calorie_target < 800 or calorie_target > 6000:
            raise ValueError("Calorie target must be between 800 and 6000")
        if not foods or len(foods) == 0:
            raise ValueError("Food dataset is empty")
        
        # Apply filters
        filtered_foods = filter_by_diet(foods, diet_type)
        filtered_foods = filter_by_allergies(filtered_foods, allergies)
        
        if not filtered_foods:
            raise ValueError(f"No foods available after applying filters (diet: {diet_type}, allergies: {allergies})")
        
        # Get calorie targets for each meal
        meal_targets = split_calories_by_meal_type(calorie_target)
        
        # Track selected meals
        selected_meals = {}
        used_recipes = set()
        
        # Select meal for each type
        meal_order = ['breakfast', 'lunch', 'dinner', 'snack']
        
        for meal_type in meal_order:
            target_calories = meal_targets[meal_type]
            min_calories = target_calories * (1 - calorie_tolerance)
            max_calories = target_calories * (1 + calorie_tolerance)
            
            # Find suitable meals in calorie range
            suitable_meals = [
                food for food in filtered_foods
                if min_calories <= food.get('Calories', 0) <= max_calories
                and food.get('RecipeName', '') not in used_recipes
            ]
            
            if not suitable_meals:
                # If no exact match, find closest meal
                suitable_meals = [
                    food for food in filtered_foods
                    if food.get('RecipeName', '') not in used_recipes
                ]
                if not suitable_meals:
                    raise ValueError(f"Not enough unique recipes available for {meal_type}")
                
                # Sort by calorie difference from target
                suitable_meals.sort(key=lambda x: abs(x.get('Calories', 0) - target_calories))
            
            # Try to find a meal with good variety
            best_meal = None
            for attempt in range(min(max_attempts, len(suitable_meals))):
                candidate = suitable_meals[attempt % len(suitable_meals)]
                
                # Check variety against already selected meals
                if ensure_variety(list(selected_meals.values()), candidate, max_same_ingredients=5):
                    best_meal = candidate
                    break
            
            # If no meal with good variety found, just take the first one
            if best_meal is None:
                best_meal = suitable_meals[0]
            
            # Add meal to plan
            selected_meals[meal_type] = best_meal
            used_recipes.add(best_meal.get('RecipeName', ''))
        
        # Calculate totals
        meals_list = list(selected_meals.values())
        total_calories, total_protein, total_carbs, total_fat = calculate_macro_totals(meals_list)
        
        # Calculate deviation
        if total_calories > 0:
            deviation = abs(total_calories - calorie_target) / calorie_target
        else:
            deviation = 1.0
        
        # Create and return meal plan
        return MealPlan(
            meals=meals_list,
            total_calories=round(total_calories, 2),
            total_protein=round(total_protein, 2),
            total_carbs=round(total_carbs, 2),
            total_fat=round(total_fat, 2),
            target_calories=calorie_target,
            calorie_deviation=round(deviation * 100, 2),
            meal_count=4
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating structured meal plan: {str(e)}"
        )


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
    
    # Get candidate ingredients (strip whitespace and filter empty strings)
    candidate_ingredients = set(
        ingredient.strip() for ingredient in candidate.get('Ingredients', '').lower().split(',')
        if ingredient.strip()
    )
    
    # Check against each selected meal
    for meal in selected_meals:
        meal_ingredients = set(
            ingredient.strip() for ingredient in meal.get('Ingredients', '').lower().split(',')
            if ingredient.strip()
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
    max_attempts: int = 100,
    shuffle: bool = True
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
        shuffle (bool): Whether to shuffle foods randomly (default True)
    
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
        best_valid_plan = None
        best_valid_deviation = float('inf')
        best_plan = None  # For diagnostics only
        best_deviation = float('inf')
        
        for attempt in range(max_attempts):
            selected_meals = []
            used_recipes = set()  # Track used recipe names to avoid duplicates
            current_calories = 0.0
            remaining_target = calorie_target
            meals_remaining = max_meals
            
            # Make a copy of available foods for this attempt
            available_foods = filtered_foods.copy()
            if shuffle:
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
                if deviation < best_valid_deviation:
                    best_valid_deviation = deviation
                    best_valid_plan = MealPlan(
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
            
            # Track best attempt for diagnostics (but don't return it)
            if deviation < best_deviation and selected_meals:
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
        
        # Return best valid plan found
        if best_valid_plan:
            return best_valid_plan
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
        calorie_tolerance=0.10,
        shuffle=False
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