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
        
        for i, meal in enumerate(meal_plan.meals):
            expected_cals = meal_plan.calorie_target * expected_percentages[i]
            actual_cals = meal.calories
            deviation = ((actual_cals - expected_cals) / expected_cals) * 100
            
            print(f"\n{meal_types[i]}")
            print(f"  Name: {meal.name}")
            print(f"  Expected: {expected_cals:.0f} kcal")
            print(f"  Actual: {actual_cals:.0f} kcal ({deviation:+.1f}% deviation)")
            print(f"  Macros: P={meal.protein}g, C={meal.carbohydrates}g, F={meal.fat}g")
            print(f"  Diet: {meal.diet_type}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"Error generating meal plan: {str(e)}")
        import traceback
        traceback.print_exc()
    
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
