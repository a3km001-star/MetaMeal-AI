"""
Macro-Aware Meal Selection Algorithm Demo

This script demonstrates the greedy optimization algorithm that:
1. Picks meals until calorie target is reached
2. Keeps calorie deviation within ±10%
3. Tracks macro totals (protein, carbs, fat)
4. Prefers meals that reduce macro deviation
5. Uses greedy optimization instead of random selection

The algorithm scores each candidate meal based on how well it fits
the remaining calorie and macro targets, then selects the best-scoring
meal at each step.
"""

from services.nutrition_engine.meal_planner import UserProfile, create_meal_plan
from services.nutrition_engine.metabolic_calculator import Sex, ActivityLevel, FitnessGoal
from fastapi import HTTPException


def safe_deviation(actual: float, target: float) -> float:
    """Calculate percentage deviation with safe division.
    
    Returns 0.0 if target is 0 and actual is also 0.
    Returns float('inf') if target is 0 but actual is not.
    """
    if target == 0:
        return 0.0 if actual == 0 else float('inf')
    return ((actual - target) / target) * 100


def display_macro_comparison(meal_plan):
    """Display how close macros are to targets."""
    print("\n" + "=" * 70)
    print("MACRO ACCURACY ANALYSIS")
    print("=" * 70)
    
    # Macro targets from the plan
    target_protein = meal_plan.macros['protein']
    target_carbs = meal_plan.macros['carbohydrates']
    target_fat = meal_plan.macros['fat']
    
    # Actual values
    actual_protein = meal_plan.total_protein
    actual_carbs = meal_plan.total_carbs
    actual_fat = meal_plan.total_fat
    
    # Calculate deviations with safe division
    protein_dev = safe_deviation(actual_protein, target_protein)
    carbs_dev = safe_deviation(actual_carbs, target_carbs)
    fat_dev = safe_deviation(actual_fat, target_fat)
    
    print(f"\nProtein:")
    print(f"  Target:  {target_protein:.1f}g")
    print(f"  Actual:  {actual_protein:.1f}g")
    print(f"  Deviation: {protein_dev:+.1f}%")
    
    print(f"\nCarbohydrates:")
    print(f"  Target:  {target_carbs:.1f}g")
    print(f"  Actual:  {actual_carbs:.1f}g")
    print(f"  Deviation: {carbs_dev:+.1f}%")
    
    print(f"\nFat:")
    print(f"  Target:  {target_fat:.1f}g")
    print(f"  Actual:  {actual_fat:.1f}g")
    print(f"  Deviation: {fat_dev:+.1f}%")
    
    # Overall macro accuracy
    avg_macro_dev = (abs(protein_dev) + abs(carbs_dev) + abs(fat_dev)) / 3
    print(f"\nAverage Macro Deviation: {avg_macro_dev:.1f}%")
    
    if avg_macro_dev < 10:
        print("✓ Excellent macro accuracy!")
    elif avg_macro_dev < 20:
        print("✓ Good macro accuracy")
    else:
        print("⚠ Macro accuracy could be improved")


def main():
    print("=" * 70)
    print("MACRO-AWARE GREEDY OPTIMIZATION DEMO")
    print("=" * 70)
    
    # Example 1: Muscle Gain (high protein focus)
    print("\n\n" + "=" * 70)
    print("Example 1: MUSCLE GAIN - High Protein Optimization")
    print("=" * 70)
    
    profile_muscle = UserProfile(
        age=25,
        weight=75,  # kg
        height=180,  # cm
        sex=Sex.MALE,
        activity_level=ActivityLevel.VERY_ACTIVE,
        goal=FitnessGoal.MUSCLE_GAIN,
        diet_type="non_veg",  # All foods for more options
        allergies=[]
    )
    
    try:
        active_profile = profile_muscle
        try:
            plan = create_meal_plan(profile_muscle)
        except HTTPException as exc:
            detail = str(exc.detail).lower()
            if "no valid meal plan generated" not in detail:
                raise
            print("Primary muscle-gain profile was infeasible; retrying with a stable fallback profile.")
            fallback_profile = UserProfile(
                age=27,
                weight=75,
                height=178,
                sex=Sex.MALE,
                activity_level=ActivityLevel.LIGHTLY_ACTIVE,
                goal=FitnessGoal.FAT_LOSS,
                diet_type="non_veg",
                allergies=[]
            )
            active_profile = fallback_profile
            plan = create_meal_plan(fallback_profile)
        
        print(f"\nTarget Calories: {plan.calorie_target:.0f} kcal")
        print(f"Actual Calories: {plan.total_calories:.0f} kcal")
        print(f"Calorie Accuracy: {plan.calorie_accuracy:.1f}%")
        
        macro_pcts = plan.macro_percentages
        print(
            f"\nMacro Targets ({active_profile.goal.value} - "
            f"{macro_pcts['protein']:.0f}% Protein, "
            f"{macro_pcts['carbohydrates']:.0f}% Carbs, "
            f"{macro_pcts['fat']:.0f}% Fat):"
        )
        print(f"  Protein: {plan.macros['protein']:.1f}g ({plan.macro_percentages['protein']:.0f}%)")
        print(f"  Carbs:   {plan.macros['carbohydrates']:.1f}g ({plan.macro_percentages['carbohydrates']:.0f}%)")
        print(f"  Fat:     {plan.macros['fat']:.1f}g ({plan.macro_percentages['fat']:.0f}%)")
        
        print(f"\n4-Meal Breakdown:")
        meal_names = ["Breakfast (25%)", "Lunch (35%)", "Dinner (30%)", "Snack (10%)"]
        for i, (meal, name) in enumerate(zip(plan.meals, meal_names)):
            print(f"\n{name}:")
            print(f"  {meal.name}")
            print(f"  Calories: {meal.calories:.0f} kcal")
            print(f"  Macros: P={meal.protein:.1f}g, C={meal.carbohydrates:.1f}g, F={meal.fat:.1f}g")
        
        display_macro_comparison(plan)
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 2: Fat Loss (calorie restricted, high protein)
    print("\n\n" + "=" * 70)
    print("Example 2: FAT LOSS - Calorie Restriction with Protein Preservation")
    print("=" * 70)
    
    profile_fatloss = UserProfile(
        age=30,
        weight=68,  # kg
        height=165,  # cm
        sex=Sex.FEMALE,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=FitnessGoal.FAT_LOSS,
        diet_type="veg",  # Vegetarian
        allergies=[]
    )
    
    try:
        plan = create_meal_plan(profile_fatloss)
        
        print(f"\nTarget Calories: {plan.calorie_target:.0f} kcal")
        print(f"Actual Calories: {plan.total_calories:.0f} kcal")
        print(f"Calorie Accuracy: {plan.calorie_accuracy:.1f}%")
        
        print(f"\nMacro Targets (Fat Loss - 40% Protein, 30% Carbs, 30% Fat):")
        print(f"  Protein: {plan.macros['protein']:.1f}g ({plan.macro_percentages['protein']:.0f}%)")
        print(f"  Carbs:   {plan.macros['carbohydrates']:.1f}g ({plan.macro_percentages['carbohydrates']:.0f}%)")
        print(f"  Fat:     {plan.macros['fat']:.1f}g ({plan.macro_percentages['fat']:.0f}%)")
        
        display_macro_comparison(plan)
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Algorithm Description
    print("\n\n" + "=" * 70)
    print("HOW THE GREEDY OPTIMIZATION WORKS")
    print("=" * 70)
    
    print("""
The macro-aware algorithm uses a fitness scoring system:

1. For each meal type (Breakfast, Lunch, Dinner, Snack):
   - Calculate remaining calorie and macro targets
   - Score all candidate meals based on:
     * Calorie match to meal target
     * How well macros fit remaining needs
     * Penalty for overshooting targets
   
2. Scoring Formula (lower is better):
   - Calorie deviation weight: 1.0
   - Macro deviation weight: 1.5 (prioritizes macro accuracy)
   - Overshoot penalty: 0.5-1.0 (avoids exceeding targets)

3. Greedy Selection:
   - Select the lowest-scoring (best-fitting) meal
   - Update remaining targets
   - Repeat for next meal

4. Optimization:
   - Try multiple iterations (100 attempts)
   - Keep best plan within ±10% calorie tolerance
   - Minimize combined calorie + macro deviation

This ensures:
✓ Calorie target is met within ±10%
✓ Macros are optimized for fitness goals
✓ No random selection - intelligent optimization
✓ Better nutritional balance
    """)


if __name__ == "__main__":
    main()
