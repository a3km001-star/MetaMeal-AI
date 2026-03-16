"""
Macro Split Calculator Module

This module converts total calories into macronutrient targets (protein, carbs, fat)
based on fitness goals. Different macro ratios are used for optimal results:
- Fat Loss: High protein, moderate carbs, moderate fat
- Muscle Gain: High protein, high carbs, moderate fat  
- Maintenance: Balanced macros

For use with FastAPI applications.
"""

from typing import Dict, Tuple, Optional
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException
from services.nutrition_engine.metabolic_calculator import FitnessGoal


# Calorie conversion constants (kcal per gram)
PROTEIN_CALORIES_PER_GRAM = 4
CARB_CALORIES_PER_GRAM = 4
FAT_CALORIES_PER_GRAM = 9


# Macro split ratios (Protein%, Carb%, Fat%) for each goal
MACRO_RATIOS: Dict[FitnessGoal, Tuple[float, float, float]] = {
    # Fat Loss: Higher protein (40%), moderate carbs (30%), moderate fat (30%)
    # High protein preserves muscle during calorie deficit
    FitnessGoal.FAT_LOSS: (0.40, 0.30, 0.30),
    
    # Muscle Gain: High protein (30%), high carbs (45%), moderate fat (25%)
    # Higher carbs for energy and muscle glycogen during training
    FitnessGoal.MUSCLE_GAIN: (0.30, 0.45, 0.25),
    
    # Maintenance: Balanced (30%, 40%, 30%)
    # Balanced approach for body composition maintenance
    FitnessGoal.MAINTENANCE: (0.30, 0.40, 0.30),
}


# Recommended protein intake per kg of body weight (for protein-priority approach)
PROTEIN_PER_KG: Dict[FitnessGoal, float] = {
    FitnessGoal.FAT_LOSS: 2.2,      # Higher to preserve muscle in deficit
    FitnessGoal.MUSCLE_GAIN: 2.0,   # Optimal for muscle building
    FitnessGoal.MAINTENANCE: 1.8,   # Maintenance level
}


class MacroSplit(BaseModel):
    """Response model for macro calculations."""
    total_calories: float = Field(..., description="Total daily calories")
    protein_grams: float = Field(..., description="Protein target in grams")
    carb_grams: float = Field(..., description="Carbohydrate target in grams")
    fat_grams: float = Field(..., description="Fat target in grams")
    protein_calories: float = Field(..., description="Calories from protein")
    carb_calories: float = Field(..., description="Calories from carbs")
    fat_calories: float = Field(..., description="Calories from fat")
    protein_percentage: float = Field(..., description="Protein as % of total calories")
    carb_percentage: float = Field(..., description="Carbs as % of total calories")
    fat_percentage: float = Field(..., description="Fat as % of total calories")
    goal: str = Field(..., description="Fitness goal used")


class MacroRequest(BaseModel):
    """Request model for macro calculation."""
    calories: float = Field(..., ge=800, le=6000, description="Target daily calories (800-6000 kcal)")
    goal: FitnessGoal = Field(..., description="Fitness goal")
    weight_kg: Optional[float] = Field(None, ge=30, le=300, description="Body weight in kg (optional)")


def calculate_macros(
    calories: float,
    goal: FitnessGoal = FitnessGoal.MAINTENANCE,
    weight_kg: Optional[float] = None
) -> MacroSplit:
    """
    Calculate macronutrient targets from total calories based on fitness goal.
    
    This function splits total daily calories into protein, carbohydrates, and fat
    using goal-specific ratios optimized for body composition:
    
    Macro Ratios:
    - Fat Loss: 40% protein, 30% carbs, 30% fat (muscle preservation)
    - Muscle Gain: 30% protein, 45% carbs, 25% fat (energy for training)
    - Maintenance: 30% protein, 40% carbs, 30% fat (balanced)
    
    If body weight is provided, protein is prioritized using recommended intake
    per kg of body weight (1.8-2.2g/kg), then remaining calories are split
    between carbs and fat.
    
    Args:
        calories (float): Target daily calories (800-6000)
        goal (FitnessGoal): Fitness goal (fat_loss, muscle_gain, maintenance)
        weight_kg (Optional[float]): Body weight in kg for protein-priority calculation
    
    Returns:
        MacroSplit: Complete macro breakdown with grams and percentages
        
    Raises:
        HTTPException: If input values are invalid
        
    Examples:
        >>> # Basic calculation (ratio-based)
        >>> macros = calculate_macros(2000, FitnessGoal.FAT_LOSS)
        >>> print(f"Protein: {macros.protein_grams}g")
        Protein: 200g
        
        >>> # With body weight (protein-priority)
        >>> macros = calculate_macros(2000, FitnessGoal.MUSCLE_GAIN, weight_kg=75)
        >>> print(f"Protein: {macros.protein_grams}g based on body weight")
        Protein: 150g based on body weight
    """
    try:
        # Validate calories
        if calories <= 0:
            raise ValueError("Calories must be positive")
        if calories < 800 or calories > 6000:
            raise ValueError("Calories must be between 800 and 6000")
        
        # Validate goal
        if goal not in MACRO_RATIOS:
            raise ValueError(f"Invalid goal: {goal}")
        
        # Choose calculation method
        if weight_kg is not None and weight_kg > 0:
            # Protein-priority approach using body weight
            return _calculate_macros_with_weight(calories, goal, weight_kg)
        else:
            # Ratio-based approach
            return _calculate_macros_by_ratio(calories, goal)
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _calculate_macros_by_ratio(calories: float, goal: FitnessGoal) -> MacroSplit:
    """
    Calculate macros using predefined ratios for each goal.
    
    Args:
        calories (float): Target daily calories
        goal (FitnessGoal): Fitness goal
        
    Returns:
        MacroSplit: Calculated macro split
    """
    # Get macro ratios for goal
    protein_ratio, carb_ratio, fat_ratio = MACRO_RATIOS[goal]
    
    # Calculate calories for each macro
    protein_calories = calories * protein_ratio
    carb_calories = calories * carb_ratio
    fat_calories = calories * fat_ratio
    
    # Convert calories to grams
    protein_grams = protein_calories / PROTEIN_CALORIES_PER_GRAM
    carb_grams = carb_calories / CARB_CALORIES_PER_GRAM
    fat_grams = fat_calories / FAT_CALORIES_PER_GRAM
    
    # Round to 1 decimal place
    protein_grams = round(protein_grams, 1)
    carb_grams = round(carb_grams, 1)
    fat_grams = round(fat_grams, 1)
    
    return MacroSplit(
        total_calories=round(calories, 1),
        protein_grams=protein_grams,
        carb_grams=carb_grams,
        fat_grams=fat_grams,
        protein_calories=round(protein_calories, 1),
        carb_calories=round(carb_calories, 1),
        fat_calories=round(fat_calories, 1),
        protein_percentage=round(protein_ratio * 100, 1),
        carb_percentage=round(carb_ratio * 100, 1),
        fat_percentage=round(fat_ratio * 100, 1),
        goal=goal.value
    )


def _calculate_macros_with_weight(
    calories: float,
    goal: FitnessGoal,
    weight_kg: float
) -> MacroSplit:
    """
    Calculate macros using protein-priority approach based on body weight.
    
    Protein is calculated first using recommended g/kg, then remaining
    calories are split between carbs and fat using goal-specific ratios.
    
    Args:
        calories (float): Target daily calories
        goal (FitnessGoal): Fitness goal
        weight_kg (float): Body weight in kg
        
    Returns:
        MacroSplit: Calculated macro split
    """
    # Validate weight
    if weight_kg < 30 or weight_kg > 300:
        raise ValueError("Weight must be between 30 and 300 kg")
    
    # Calculate protein based on body weight
    protein_per_kg = PROTEIN_PER_KG[goal]
    protein_grams = weight_kg * protein_per_kg
    protein_calories = protein_grams * PROTEIN_CALORIES_PER_GRAM
    
    # Ensure protein doesn't exceed 50% of total calories
    max_protein_calories = calories * 0.50
    if protein_calories > max_protein_calories:
        protein_calories = max_protein_calories
        protein_grams = protein_calories / PROTEIN_CALORIES_PER_GRAM
    
    # Remaining calories for carbs and fat
    remaining_calories = calories - protein_calories
    
    # Get carb and fat ratios for goal (excluding protein)
    _, carb_ratio, fat_ratio = MACRO_RATIOS[goal]
    
    # Recalculate carb/fat ratios from remaining calories
    non_protein_total = carb_ratio + fat_ratio
    carb_remaining_ratio = carb_ratio / non_protein_total
    fat_remaining_ratio = fat_ratio / non_protein_total
    
    # Calculate carb and fat calories
    carb_calories = remaining_calories * carb_remaining_ratio
    fat_calories = remaining_calories * fat_remaining_ratio
    
    # Convert to grams
    carb_grams = carb_calories / CARB_CALORIES_PER_GRAM
    fat_grams = fat_calories / FAT_CALORIES_PER_GRAM
    
    # Round to 1 decimal place
    protein_grams = round(protein_grams, 1)
    carb_grams = round(carb_grams, 1)
    fat_grams = round(fat_grams, 1)
    
    # Calculate actual percentages
    protein_percentage = (protein_calories / calories) * 100
    carb_percentage = (carb_calories / calories) * 100
    fat_percentage = (fat_calories / calories) * 100
    
    return MacroSplit(
        total_calories=round(calories, 1),
        protein_grams=protein_grams,
        carb_grams=carb_grams,
        fat_grams=fat_grams,
        protein_calories=round(protein_calories, 1),
        carb_calories=round(carb_calories, 1),
        fat_calories=round(fat_calories, 1),
        protein_percentage=round(protein_percentage, 1),
        carb_percentage=round(carb_percentage, 1),
        fat_percentage=round(fat_percentage, 1),
        goal=goal.value
    )


def validate_macro_totals(
    protein_grams: float,
    carb_grams: float,
    fat_grams: float,
    expected_calories: float,
    tolerance: float = 0.05
) -> bool:
    """
    Validate that macro totals match expected calorie target.
    
    Uses the formula: (Protein × 4) + (Carbs × 4) + (Fat × 9) = Total Calories
    
    Args:
        protein_grams (float): Protein in grams
        carb_grams (float): Carbohydrates in grams
        fat_grams (float): Fat in grams
        expected_calories (float): Expected total calories
        tolerance (float): Acceptable deviation (default 5%)
        
    Returns:
        bool: True if macros match expected calories within tolerance
        
    Raises:
        ValueError: If input values are invalid
        
    Example:
        >>> valid = validate_macro_totals(150, 200, 67, 2000)
        >>> print(f"Macros are valid: {valid}")
        Macros are valid: True
    """
    # Validate inputs – return False for invalid arguments to preserve the bool contract.
    if expected_calories <= 0:
        return False
    if tolerance < 0:
        return False
    if protein_grams < 0 or carb_grams < 0 or fat_grams < 0:
        return False
    
    # Calculate actual calories from macros
    calculated_calories = (
        (protein_grams * PROTEIN_CALORIES_PER_GRAM) +
        (carb_grams * CARB_CALORIES_PER_GRAM) +
        (fat_grams * FAT_CALORIES_PER_GRAM)
    )
    
    # Calculate deviation
    deviation = abs(calculated_calories - expected_calories)
    max_deviation = expected_calories * tolerance
    
    return deviation <= max_deviation


def get_macro_percentages(
    protein_grams: float,
    carb_grams: float,
    fat_grams: float
) -> Tuple[float, float, float]:
    """
    Calculate percentage of total calories from each macronutrient.
    
    Args:
        protein_grams (float): Protein in grams
        carb_grams (float): Carbohydrates in grams
        fat_grams (float): Fat in grams
        
    Returns:
        Tuple[float, float, float]: (protein%, carb%, fat%) rounded to 1 decimal
        
    Example:
        >>> protein_pct, carb_pct, fat_pct = get_macro_percentages(150, 200, 67)
        >>> print(f"P: {protein_pct}%, C: {carb_pct}%, F: {fat_pct}%")
        P: 30.0%, C: 40.0%, F: 30.0%
    """
    # Calculate total calories
    total_calories = (
        (protein_grams * PROTEIN_CALORIES_PER_GRAM) +
        (carb_grams * CARB_CALORIES_PER_GRAM) +
        (fat_grams * FAT_CALORIES_PER_GRAM)
    )
    
    if total_calories == 0:
        return (0.0, 0.0, 0.0)
    
    # Calculate percentages
    protein_pct = ((protein_grams * PROTEIN_CALORIES_PER_GRAM) / total_calories) * 100
    carb_pct = ((carb_grams * CARB_CALORIES_PER_GRAM) / total_calories) * 100
    fat_pct = ((fat_grams * FAT_CALORIES_PER_GRAM) / total_calories) * 100
    
    return (
        round(protein_pct, 1),
        round(carb_pct, 1),
        round(fat_pct, 1)
    )


def get_recommended_protein(weight_kg: float, goal: FitnessGoal) -> float:
    """
    Get recommended protein intake in grams based on body weight and goal.
    
    Recommendations:
    - Fat Loss: 2.2g per kg (muscle preservation in deficit)
    - Muscle Gain: 2.0g per kg (optimal for hypertrophy)
    - Maintenance: 1.8g per kg (general health)
    
    Args:
        weight_kg (float): Body weight in kilograms
        goal (FitnessGoal): Fitness goal
        
    Returns:
        float: Recommended protein in grams
        
    Example:
        >>> protein = get_recommended_protein(75, FitnessGoal.MUSCLE_GAIN)
        >>> print(f"Recommended protein: {protein}g")
        Recommended protein: 150g
    """
    if weight_kg < 30 or weight_kg > 300:
        raise ValueError("Weight must be between 30 and 300 kg")
    
    protein_per_kg = PROTEIN_PER_KG.get(goal, 2.0)
    return round(weight_kg * protein_per_kg, 1)


def get_macro_split_description(goal: FitnessGoal) -> str:
    """
    Get human-readable description of macro split for a goal.
    
    Args:
        goal (FitnessGoal): Fitness goal
        
    Returns:
        str: Description of macro ratios
    """
    descriptions = {
        FitnessGoal.FAT_LOSS: "40% Protein / 30% Carbs / 30% Fat - Optimized for fat loss and muscle preservation",
        FitnessGoal.MUSCLE_GAIN: "30% Protein / 45% Carbs / 25% Fat - Optimized for muscle building and recovery",
        FitnessGoal.MAINTENANCE: "30% Protein / 40% Carbs / 30% Fat - Balanced for weight maintenance",
    }
    return descriptions.get(goal, "Unknown macro split")