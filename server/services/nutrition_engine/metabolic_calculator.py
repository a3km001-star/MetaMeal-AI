"""
Metabolic Calculator Module

This module provides functions to calculate metabolic values including:
- BMR (Basal Metabolic Rate) using Mifflin-St Jeor equation
- TDEE (Total Daily Energy Expenditure)
- Calorie adjustments based on fitness goals

"""

from enum import Enum
from typing import Dict, Tuple, Optional
from pydantic import BaseModel, Field, field_validator
from fastapi import HTTPException


class Sex(str, Enum):
    """Biological sex for BMR calculation."""
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, Enum):
    """Activity level categories for TDEE calculation."""
    SEDENTARY = "sedentary"  # Little or no exercise
    LIGHTLY_ACTIVE = "lightly_active"  # Light exercise 1-3 days/week
    MODERATELY_ACTIVE = "moderately_active"  # Moderate exercise 3-5 days/week
    VERY_ACTIVE = "very_active"  # Hard exercise 6-7 days/week


class FitnessGoal(str, Enum):
    """Fitness goal categories for calorie adjustment."""
    FAT_LOSS = "fat_loss"  # Weight loss / cutting
    MUSCLE_GAIN = "muscle_gain"  # Muscle building / bulking
    MAINTENANCE = "maintenance"  # Maintain current weight
    ENDURANCE = "endurance"  # Performance/endurance support


# Activity level multipliers for TDEE calculation
ACTIVITY_MULTIPLIERS: Dict[ActivityLevel, float] = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHTLY_ACTIVE: 1.375,
    ActivityLevel.MODERATELY_ACTIVE: 1.55,
    ActivityLevel.VERY_ACTIVE: 1.725,
}


# Goal-based calorie adjustments (percentage)
GOAL_ADJUSTMENTS: Dict[FitnessGoal, float] = {
    FitnessGoal.FAT_LOSS: -0.20,  # 20% deficit for fat loss
    FitnessGoal.MUSCLE_GAIN: 0.15,  # 15% surplus for muscle gain
    FitnessGoal.MAINTENANCE: 0.0,  # No adjustment for maintenance
    FitnessGoal.ENDURANCE: 0.05,  # Small surplus for endurance training support
}


class MetabolicRequest(BaseModel):
    """Request model for complete metabolic calculation."""
    age: int = Field(..., ge=15, le=100, description="Age in years")
    weight: float = Field(..., ge=30, le=300, description="Weight in kilograms")
    height: float = Field(..., ge=100, le=250, description="Height in centimeters")
    sex: Sex = Field(..., description="Biological sex (male/female)")
    activity_level: ActivityLevel = Field(..., description="Physical activity level")
    goal: FitnessGoal = Field(..., description="Fitness goal")

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v):
        """Validate weight is reasonable."""
        if v < 30 or v > 300:
            raise ValueError("Weight must be between 30 and 300 kg")
        return v

    @field_validator("height")
    @classmethod
    def validate_height(cls, v):
        """Validate height is reasonable."""
        if v < 100 or v > 250:
            raise ValueError("Height must be between 100 and 250 cm")
        return v


class MetabolicResponse(BaseModel):
    """Response model for metabolic calculations."""
    bmr: float = Field(..., description="Basal Metabolic Rate (kcal/day)")
    tdee: float = Field(..., description="Total Daily Energy Expenditure (kcal/day)")
    target_calories: float = Field(..., description="Target calories for goal (kcal/day)")
    activity_level: str = Field(..., description="Activity level used")
    goal: str = Field(..., description="Fitness goal")
    adjustment_percentage: float = Field(..., description="Calorie adjustment percentage")


def calculate_bmr(age: int, weight: float, height: float, sex: Sex) -> float:
    """
    Calculate Basal Metabolic Rate (BMR) using Mifflin-St Jeor equation.
    
    The Mifflin-St Jeor equation is considered one of the most accurate
    methods for estimating BMR.
    
    Formula:
    - Men: BMR = (10 × weight in kg) + (6.25 × height in cm) - (5 × age) + 5
    - Women: BMR = (10 × weight in kg) + (6.25 × height in cm) - (5 × age) - 161
    
    Args:
        age (int): Age in years (15-100)
        weight (float): Body weight in kilograms (30-300)
        height (float): Height in centimeters (100-250)
        sex (Sex): Biological sex (male/female)
    
    Returns:
        float: Basal Metabolic Rate in kcal/day
        
    Raises:
        HTTPException: If input values are invalid
        
    Example:
        >>> bmr = calculate_bmr(age=25, weight=70, height=175, sex=Sex.MALE)
        >>> print(f"BMR: {bmr:.2f} kcal/day")
        BMR: 1673.75 kcal/day
    """
    try:
        # Validate inputs
        if not (15 <= age <= 100):
            raise ValueError("Age must be between 15 and 100 years")
        if not (30 <= weight <= 300):
            raise ValueError("Weight must be between 30 and 300 kg")
        if not (100 <= height <= 250):
            raise ValueError("Height must be between 100 and 250 cm")
        
        # Mifflin-St Jeor equation
        bmr = (10 * weight) + (6.25 * height) - (5 * age)
        
        # Add sex-specific adjustment
        if sex == Sex.MALE:
            bmr += 5
        elif sex == Sex.FEMALE:
            bmr -= 161
        else:
            raise ValueError(f"Invalid sex value: {sex}")
        
        return round(bmr, 2)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating BMR: {str(e)}"
        )


def calculate_tdee(bmr: float, activity_level: ActivityLevel) -> float:
    """
    Calculate Total Daily Energy Expenditure (TDEE).
    
    TDEE is calculated by multiplying BMR by an activity factor that
    accounts for physical activity level.
    
    Activity Level Multipliers:
    - Sedentary (little/no exercise): BMR × 1.2
    - Lightly Active (1-3 days/week): BMR × 1.375
    - Moderately Active (3-5 days/week): BMR × 1.55
    - Very Active (6-7 days/week): BMR × 1.725
    
    Args:
        bmr (float): Basal Metabolic Rate in kcal/day
        activity_level (ActivityLevel): Physical activity level
    
    Returns:
        float: Total Daily Energy Expenditure in kcal/day
        
    Raises:
        HTTPException: If input values are invalid
        
    Example:
        >>> tdee = calculate_tdee(bmr=1673.75, activity_level=ActivityLevel.MODERATELY_ACTIVE)
        >>> print(f"TDEE: {tdee:.2f} kcal/day")
        TDEE: 2594.31 kcal/day
    """
    try:
        # Validate BMR
        if bmr <= 0:
            raise ValueError("BMR must be positive")
        
        # Get activity multiplier
        if activity_level not in ACTIVITY_MULTIPLIERS:
            raise ValueError(f"Invalid activity level: {activity_level}")
        
        multiplier = ACTIVITY_MULTIPLIERS[activity_level]
        tdee = bmr * multiplier
        
        return round(tdee, 2)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating TDEE: {str(e)}"
        )


def adjust_for_goal(tdee: float, goal: FitnessGoal, sex: Optional[Sex] = None) -> float:
    """
    Adjust TDEE based on fitness goal.
    
    Calorie adjustments:
    - Fat Loss: -20% (creates calorie deficit)
    - Muscle Gain: +10% (creates calorie surplus)
    - Maintenance: 0% (no change)
    
    Enforces minimum calorie floors for safety:
    - Women: 1200 kcal/day minimum
    - Men: 1500 kcal/day minimum
    - If sex not specified: 1200 kcal/day minimum
    
    Args:
        tdee (float): Total Daily Energy Expenditure in kcal/day
        goal (FitnessGoal): Fitness goal (fat_loss, muscle_gain, maintenance)
        sex (Optional[Sex]): Biological sex for appropriate calorie floor
    
    Returns:
        float: Adjusted target calories in kcal/day
        
    Raises:
        HTTPException: If input values are invalid
        
    Example:
        >>> target = adjust_for_goal(tdee=2594.31, goal=FitnessGoal.FAT_LOSS)
        >>> print(f"Target: {target:.2f} kcal/day")
        Target: 2075.45 kcal/day
    """
    try:
        # Validate TDEE
        if tdee <= 0:
            raise ValueError("TDEE must be positive")
        
        # Get goal adjustment
        if goal not in GOAL_ADJUSTMENTS:
            raise ValueError(f"Invalid goal: {goal}")
        
        adjustment = GOAL_ADJUSTMENTS[goal]
        target_calories = tdee * (1 + adjustment)
        
        # Ensure minimum calories for safety (sex-specific floors)
        if sex == Sex.MALE:
            min_calories = 1500
        elif sex == Sex.FEMALE:
            min_calories = 1200
        else:
            # Default to conservative minimum if sex not specified
            min_calories = 1200
        
        if target_calories < min_calories:
            target_calories = min_calories
        
        return round(target_calories, 2)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adjusting for goal: {str(e)}"
        )


def calculate_complete_metabolic_profile(
    age: int,
    weight: float,
    height: float,
    sex: Sex,
    activity_level: ActivityLevel,
    goal: FitnessGoal
) -> MetabolicResponse:
    """
    Calculate complete metabolic profile including BMR, TDEE, and target calories.
    
    This is a convenience function that combines all three calculations
    and returns a complete metabolic profile.
    
    Args:
        age (int): Age in years
        weight (float): Weight in kilograms
        height (float): Height in centimeters
        sex (Sex): Biological sex
        activity_level (ActivityLevel): Physical activity level
        goal (FitnessGoal): Fitness goal
    
    Returns:
        MetabolicResponse: Complete metabolic profile
        
    Example:
        >>> profile = calculate_complete_metabolic_profile(
        ...     age=25, weight=70, height=175, sex=Sex.MALE,
        ...     activity_level=ActivityLevel.MODERATELY_ACTIVE,
        ...     goal=FitnessGoal.FAT_LOSS
        ... )
        >>> print(f"Target Calories: {profile.target_calories} kcal/day")
    """
    # Calculate BMR
    bmr = calculate_bmr(age, weight, height, sex)
    
    # Calculate TDEE
    tdee = calculate_tdee(bmr, activity_level)
    
    # Adjust for goal
    target_calories = adjust_for_goal(tdee, goal, sex)
    
    # Get adjustment percentage
    adjustment_percentage = GOAL_ADJUSTMENTS[goal] * 100
    
    return MetabolicResponse(
        bmr=bmr,
        tdee=tdee,
        target_calories=target_calories,
        activity_level=activity_level.value,
        goal=goal.value,
        adjustment_percentage=adjustment_percentage
    )


def get_activity_level_description(activity_level: ActivityLevel) -> str:
    """
    Get human-readable description of activity level.
    
    Args:
        activity_level (ActivityLevel): Activity level enum
        
    Returns:
        str: Description of the activity level
    """
    descriptions = {
        ActivityLevel.SEDENTARY: "Little or no exercise, desk job",
        ActivityLevel.LIGHTLY_ACTIVE: "Light exercise 1-3 days per week",
        ActivityLevel.MODERATELY_ACTIVE: "Moderate exercise 3-5 days per week",
        ActivityLevel.VERY_ACTIVE: "Hard exercise 6-7 days per week",
    }
    return descriptions.get(activity_level, "Unknown activity level")


def get_goal_description(goal: FitnessGoal) -> str:
    """
    Get human-readable description of fitness goal.
    
    Args:
        goal (FitnessGoal): Fitness goal enum
        
    Returns:
        str: Description of the fitness goal
    """
    descriptions = {
        FitnessGoal.FAT_LOSS: "Lose fat while preserving muscle (20% calorie deficit)",
        FitnessGoal.MUSCLE_GAIN: "Build muscle and strength (10% calorie surplus)",
        FitnessGoal.MAINTENANCE: "Maintain current weight and composition",
    }
    return descriptions.get(goal, "Unknown goal")
