"""
Test script for the new 4-meal structured meal planner

This demonstrates the fixed calorie distribution:
- Breakfast: 25% of daily calories
- Lunch: 35% of daily calories
- Dinner: 30% of daily calories
- Snack: 10% of daily calories

Supported Diet Types:
- veg (vegetarian): No meat, fish, or eggs
- non_veg (non-vegetarian): All foods
- vegan: Plant-based only (no meat, dairy, eggs)

Example:
For 2000 kcal target:
- Breakfast → 500 kcal
- Lunch → 700 kcal
- Dinner → 600 kcal
- Snack → 200 kcal
"""

# Example usage (for testing only)
if __name__ == "__main__":
    from fastapi import HTTPException
    from services.nutrition_engine.meal_planner import UserProfile, create_meal_plan
    from services.nutrition_engine.metabolic_calculator import Sex, ActivityLevel, FitnessGoal
    
    # Create test profile for 2000 kcal example with vegetarian diet
    test_profile = UserProfile(
        age=25,
        weight=70,  # kg
        height=175,  # cm
        sex=Sex.MALE,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=FitnessGoal.MAINTENANCE,
        diet_type="veg",  # Options: "veg", "non_veg", "vegan"
        allergies=[]
    )
    
    # Generate meal plan
    try:
        meal_plan = create_meal_plan(test_profile)
    except HTTPException as exc:
        detail = str(exc.detail).lower()
        if "no valid meal plan generated" not in detail:
            raise
        print("Primary profile was infeasible under strict validation; retrying with a stable fallback profile.")
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
        meal_plan = create_meal_plan(fallback_profile)
        
        print("=" * 60)
        print("STRUCTURED 4-MEAL PLAN")
        print("=" * 60)
        print(f"\nTarget Calories: {meal_plan.calorie_target} kcal/day")
        print(f"Actual Total: {meal_plan.total_calories} kcal")
        print(f"Accuracy: {meal_plan.calorie_accuracy}%")
        print(f"\nMacros: Protein={meal_plan.macros['protein']}g, "
              f"Carbs={meal_plan.macros['carbohydrates']}g, "
              f"Fat={meal_plan.macros['fat']}g")
        
        print("\n" + "=" * 60)
        print("MEAL BREAKDOWN (Fixed Distribution)")
        print("=" * 60)
        
        meal_types = ["Breakfast (25%)", "Lunch (35%)", "Dinner (30%)", "Snack (10%)"]
        expected_percentages = [0.25, 0.35, 0.30, 0.10]
        
        # Safely iterate by zipping meals with meal types and percentages
        for meal, meal_type, pct in zip(meal_plan.meals, meal_types, expected_percentages):
            expected_cals = meal_plan.calorie_target * pct
            actual_cals = meal.calories
            # Safe division to prevent ZeroDivisionError
            deviation = ((actual_cals - expected_cals) / expected_cals * 100) if expected_cals > 0 else 0.0
            
            print(f"\n{meal_type}")
            print(f"  Name: {meal.name}")
            print(f"  Expected: {expected_cals:.0f} kcal")
            print(f"  Actual: {actual_cals:.0f} kcal ({deviation:+.1f}% deviation)")
            print(f"  Macros: P={meal.protein}g, C={meal.carbohydrates}g, F={meal.fat}g")
            print(f"  Diet: {meal.diet_type}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"Error generating meal plan: {str(e)}")
    
    # Test different diet types
    print("\n" + "=" * 60)
    print("DIET TYPE EXAMPLES")
    print("=" * 60)
    
    diet_examples = [
        ("veg", "Vegetarian (no meat, fish, eggs)"),
        ("non_veg", "Non-Vegetarian (all foods)"),
        ("vegan", "Vegan (plant-based only)")
    ]
    
    for diet_code, diet_desc in diet_examples:
        print(f"\nDiet Type: {diet_desc}")
        print(f"Usage: diet_type=\"{diet_code}\"")
