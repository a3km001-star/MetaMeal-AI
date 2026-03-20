"""
Comprehensive Test Suite for Meal Planner

Tests the complete meal planning workflow including all helper functions.
Run with: python test_meal_planner.py
"""

import re

from services.nutrition_engine.meal_planner import (
    create_meal_plan,
    get_meal_plan_summary,
    validate_user_profile,
    get_daily_meal_distribution,
    compare_plan_to_targets,
    UserProfile,
    Sex,
    ActivityLevel,
    FitnessGoal
)
from services.nutrition_engine.metabolic_calculator import (
    calculate_bmr,
    calculate_tdee,
    adjust_for_goal,
)
from fastapi import HTTPException
import traceback


def _assert_plan_invariants(plan, profile):
    """Validate core invariants for a generated meal plan."""
    assert plan.bmr > 0, "BMR must be positive"
    assert plan.tdee > plan.bmr, "TDEE must be greater than BMR"
    assert plan.total_calories > 0, "Total calories must be positive"
    assert plan.meal_count == 4, f"Expected fixed 4-meal plan, got {plan.meal_count}"
    assert len(plan.meals) == 4, f"Expected 4 meal items, got {len(plan.meals)}"
    assert 0 <= plan.calorie_accuracy <= 100, f"Accuracy must be between 0 and 100, got {plan.calorie_accuracy}"

    if profile.goal == FitnessGoal.FAT_LOSS:
        assert plan.calorie_target < plan.tdee, (
            f"Fat loss target should be less than TDEE (got {plan.calorie_target} vs {plan.tdee})"
        )
    elif profile.goal == FitnessGoal.MUSCLE_GAIN:
        assert plan.calorie_target > plan.tdee, (
            f"Muscle gain target should exceed TDEE (got {plan.calorie_target} vs {plan.tdee})"
        )
    else:
        assert plan.calorie_target == plan.tdee, (
            f"Maintenance target should equal TDEE (got {plan.calorie_target} vs {plan.tdee})"
        )


def _assert_allergens_excluded(plan, allergies):
    """Ensure generated meal ingredients do not contain the requested allergens."""
    for meal in plan.meals:
        ingredients_lower = meal.ingredients.lower()
        for allergen in allergies:
            pattern = rf"\b{re.escape(allergen.lower())}\b"
            assert not re.search(pattern, ingredients_lower), (
                f"Allergen '{allergen}' found in meal '{meal.name}'"
            )


def _build_basic_profile():
    """Stable smoke-test profile for the current macro-aware planner."""
    return UserProfile(
        age=27,
        weight=75,
        height=178,
        sex=Sex.MALE,
        activity_level=ActivityLevel.LIGHTLY_ACTIVE,
        goal=FitnessGoal.FAT_LOSS,
        diet_type="non_veg",
        allergies=[]
    )


def _build_allergy_profile():
    """Stable allergy-aware profile that still succeeds under current constraints."""
    return UserProfile(
        age=27,
        weight=68,
        height=165,
        sex=Sex.FEMALE,
        activity_level=ActivityLevel.SEDENTARY,
        goal=FitnessGoal.MUSCLE_GAIN,
        diet_type="non_veg",
        allergies=["milk"]
    )


def test_basic_meal_plan():
    """Test 1: Basic Meal Plan Generation - Male, 27 years, Fat Loss"""
    print("\n" + "=" * 70)
    print("TEST 1: Male, 27 years, Fat Loss Goal")
    print("=" * 70)
    
    profile = _build_basic_profile()
    
    print(f"\nUser Profile: {profile.age}y, {profile.weight}kg, {profile.height}cm")
    print(f"  Goal: {profile.goal.value}, Activity: {profile.activity_level.value}")
    
    plan = create_meal_plan(profile)
    
    _assert_plan_invariants(plan, profile)
    assert plan.calorie_accuracy >= 90, f"Accuracy {plan.calorie_accuracy}% is below 90% threshold"
    
    print(f"\n✓ Metabolic: BMR={plan.bmr}, TDEE={plan.tdee}, Target={plan.calorie_target}")
    print(f"✓ Macros: P={plan.macros['protein']:.0f}g, C={plan.macros['carbohydrates']:.0f}g, F={plan.macros['fat']:.0f}g")
    print(f"✓ Meal Plan: {plan.meal_count} meals, {plan.total_calories} kcal, {plan.calorie_accuracy:.1f}% accuracy")


def test_allergies_meal_plan():
    """Test 2: Female, Muscle Gain with Allergies"""
    print("\n" + "=" * 70)
    print("TEST 2: Female, 28 years, Muscle Gain, With Allergies")
    print("=" * 70)
    
    profile = _build_allergy_profile()
    
    print(f"\nProfile: {profile.age}y, {profile.weight}kg, Goal: {profile.goal.value}")
    print(f"Allergies: {', '.join(profile.allergies) if profile.allergies else 'None'}")

    plan = create_meal_plan(profile)

    _assert_plan_invariants(plan, profile)
    _assert_allergens_excluded(plan, profile.allergies or [])

    print(f"\n✓ Target: {plan.calorie_target} kcal/day ({plan.meal_count} meals)")
    print(f"✓ Accuracy: {plan.calorie_accuracy:.1f}%")
    print(f"✓ All {plan.meal_count} meals are allergen-safe")


def test_helper_functions():
    """Test 3-6: Helper Functions"""
    print("\n" + "=" * 70)
    print("TEST 3: Helper Functions")
    print("=" * 70)

    sample_plan = create_meal_plan(_build_basic_profile())
    
    # Test meal plan summary
    summary = get_meal_plan_summary(sample_plan)
    assert 'meal_count' in summary, "Summary missing meal_count"
    assert 'total_calories' in summary, "Summary missing total_calories"
    assert summary['meal_count'] == 4, f"Expected summary meal_count 4, got {summary['meal_count']}"
    print(f"\n✓ get_meal_plan_summary: {summary['meal_count']} meals, {summary['accuracy']}")
    
    # Test profile validation
    raw_data = {
        "age": 35,
        "weight": 75,
        "height": 175,
        "sex": "male",
        "activity_level": "lightly_active",
        "goal": "maintenance",
        "diet_type": "veg"
    }
    validated = validate_user_profile(raw_data)
    assert validated.age == 35, "Profile validation failed"
    assert validated.diet_type == "veg", "Diet type should be preserved during validation"
    print(f"✓ validate_user_profile: validated {validated.age}y, {validated.goal.value}")
    
    # Test meal distribution
    dist = get_daily_meal_distribution(2000, 3)
    assert 'breakfast' in dist, "Missing breakfast in distribution"
    assert 'lunch' in dist, "Missing lunch in distribution"
    assert 'dinner' in dist, "Missing dinner in distribution"
    print(f"✓ get_daily_meal_distribution: {list(dist.keys())}")
    
    # Test comparison
    comparison = compare_plan_to_targets(sample_plan)
    assert 'calories' in comparison, "Missing calories in comparison"
    assert 'protein' in comparison, "Missing protein in comparison"
    assert comparison['calories']['percentage'] > 0, "Invalid calorie percentage"
    print(f"✓ compare_plan_to_targets: {comparison['calories']['percentage']:.1f}% calorie match")


def test_different_goals():
    """Test 7-8: Different Activity Levels and Goals"""
    print("\n" + "=" * 70)
    print("TEST 4: Different Goals and Activity Levels")
    print("=" * 70)
    
    base_profile = {
        "age": 27,
        "weight": 68,
        "height": 165,
        "sex": "female",
        "activity_level": "lightly_active",
        "diet_type": "non_veg"
    }
    
    goals = [
        "fat_loss",
        "maintenance",
        "muscle_gain"
    ]
    
    results = []
    for goal_name in goals:
        profile_data = {**base_profile, "goal": goal_name}
        profile = validate_user_profile(profile_data)

        bmr = calculate_bmr(
            age=profile.age,
            weight=profile.weight,
            height=profile.height,
            sex=profile.sex,
        )
        tdee = calculate_tdee(bmr=bmr, activity_level=profile.activity_level)
        calorie_target = adjust_for_goal(tdee=tdee, goal=profile.goal, sex=profile.sex)

        results.append((goal_name, calorie_target))
        print(f"  {goal_name:15s}: {calorie_target:.0f} kcal")
    
    # Verify ordering: fat_loss < maintenance < muscle_gain
    fat_loss_cal = results[0][1]
    maintenance_cal = results[1][1]
    muscle_gain_cal = results[2][1]
    
    assert fat_loss_cal < maintenance_cal, "Fat loss should have fewer calories than maintenance"
    assert maintenance_cal < muscle_gain_cal, "Maintenance should have fewer calories than muscle gain"
    
    print(f"\n✓ Calorie targets correct: {fat_loss_cal:.0f} < {maintenance_cal:.0f} < {muscle_gain_cal:.0f}")


def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "=" * 70)
    print("TEST 5: Edge Cases and Error Handling")
    print("=" * 70)
    
    # Test with very restrictive constraints
    profile = UserProfile(
        age=20,
        weight=50,
        height=160,
        sex=Sex.FEMALE,
        activity_level=ActivityLevel.SEDENTARY,
        goal=FitnessGoal.FAT_LOSS,
        diet_type="veg",
        allergies=["milk", "paneer", "ghee", "butter"]
    )
    
    try:
        plan = create_meal_plan(profile)
        _assert_plan_invariants(plan, profile)
        _assert_allergens_excluded(plan, profile.allergies or [])
        print(f"✓ Handled restrictive constraints: {plan.meal_count} meals generated")
    except HTTPException as e:
        error_msg = str(e.detail)
        if "Unable to generate meal plan" in error_msg or "No foods available" in error_msg:
            print(f"✓ Correctly raised HTTPException for restrictive constraints")
            print(f"  Message: {error_msg[:80]}...")
        else:
            print(f"✗ Unexpected error: {error_msg}")
            raise


def run_all_tests():
    """Run all tests and report results"""
    print("=" * 70)
    print("MEAL PLANNER TEST SUITE")
    print("=" * 70)
    
    all_passed = True
    failures = []

    tests = [
        ("Basic meal plan generation", test_basic_meal_plan),
        ("Allergy-aware meal plan generation", test_allergies_meal_plan),
        ("Helper functions", test_helper_functions),
        ("Goal-based calorie ordering", test_different_goals),
        ("Edge cases and error handling", test_edge_cases),
    ]

    for test_name, test_func in tests:
        try:
            test_func()
        except AssertionError as e:
            all_passed = False
            failures.append(f"{test_name}: Assertion failed: {str(e)}")
            print(f"\n✗ ASSERTION FAILED in {test_name}: {e}")
            traceback.print_exc()
        except Exception as e:
            all_passed = False
            failures.append(f"{test_name}: Unexpected error: {str(e)}")
            print(f"\n✗ UNEXPECTED ERROR in {test_name}: {e}")
            traceback.print_exc()
    
    # Final Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nTest Summary:")
        print("  ✓ Basic meal plan generation (Male, Fat Loss)")
        print("  ✓ Meal plan with allergies (Female, Muscle Gain)")
        print("  ✓ Helper functions (summary, validation, distribution, comparison)")
        print("  ✓ Different fitness goals (fat loss, maintenance, muscle gain)")
        print("  ✓ Edge cases and error handling")
        print("\nAll modules tested successfully:")
        print("  ✓ helpers.py - Dataset loading")
        print("  ✓ metabolic_calculator.py - BMR, TDEE, goal adjustment")
        print("  ✓ macro_split.py - Macro calculations")
        print("  ✓ constraint_solver.py - Meal selection")
        print("  ✓ meal_planner.py - Master orchestration")
        print("\n" + "=" * 70)
        print("Meal planner is ready for integration testing!")
        print("=" * 70)
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 70)
        print("\nFailures:")
        for failure in failures:
            print(f"  - {failure}")
        print("\n" + "=" * 70)
    
    return all_passed


def main():
    """Main entry point"""
    success = run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
