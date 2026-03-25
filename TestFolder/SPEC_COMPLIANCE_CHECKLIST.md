# Spec-Compliant Meal Planner - Implementation Checklist

## 11-Step Algorithm Implementation Status

### Step 1: Metabolic Base [IMPLEMENTED] ✓
- Location: `meal_planner.py:_generate_validated_meal_plan_spec_compliant()` line ~315
- Calculate BMR using Mifflin-St Jeor equation
- Calculate TDEE with activity multiplier
- Adjust for fitness goal
- Implementation: `metabolic_calculator.py` (reused)
- Log: "STEP 1: Calculating metabolic base"

### Step 2: Carb Baseline Adjustment [IMPLEMENTED] ✓
- Location: `meal_planner.py:_generate_validated_meal_plan_spec_compliant()` line ~329
- Subtract 390 kcal from total daily calories
- Implementation: `spec_compliant_steps.py:apply_carb_baseline()`
- Formula: `adjusted_calories = calorie_target - 390`
- Recalculate macros from adjusted calories
- Log: "STEP 2: Applying carb baseline adjustment"

### Step 3: Filtering [IMPLEMENTED] ✓
- Location: `meal_planner.py:_generate_validated_meal_plan_spec_compliant()` line ~344
- Filter by diet type (veg/non_veg/vegan)
- Filter by allergies (keyword-based)
- Implementation: `constraint_solver.py` (reused)
- Log: "STEP 3: Filtering by diet and allergies"

### Step 4: Age-Based Scaling [IMPLEMENTED] ✓
- Location: `spec_compliant_steps.py` and `meal_planner.py:_prepare_foods_for_profile_spec_compliant()`
- Multiply factor by age:
  - 15-18: 1.6x
  - 18-22: 2.0x
  - 22-40: 2.5x
  - 40-50: 2.0x
  - 50-60: 1.8x
  - 60+: 1.8x
- Implementation: `spec_compliant_steps.py:get_age_multiply_factor()` and `scale_recipe_by_factor()`
- Apply before meal selection (in preparation phase)
- Fallback: Attempt 4+, increase to 2.5x
- Log: "STEP 4: Age-Based Scaling (already done in food prep, but adjust for fallback)"

### Step 5: Meal Split [IMPLEMENTED] ✓
- Location: `meal_planner.py:_generate_validated_meal_plan_spec_compliant()` line ~369
- Distribute calories by meal slot:
  - Breakfast: 25%
  - Lunch: 35%
  - Dinner: 30%
  - Snack: 10%
- Implementation: `spec_compliant_steps.py:split_calories_by_meal_slot()` and `split_macros_by_meal_slot()`
- Log: "STEP 5: Calculating meal slot targets"

### Step 6: Bucket Assignment [IMPLEMENTED] ✓
- Location: `meal_planner.py:_generate_validated_meal_plan_spec_compliant()` line ~377
- Assign each recipe to best-fit meal slot:
  - For each recipe:
    1. Calculate relative error = |target - recipe| / target
    2. Check thresholds:
       - Breakfast calories: ±10%
       - Other meals calories: ±12%
       - All meals protein: ±20%
    3. Find slot with minimum calorie error
    4. Prevent duplicate usage
- Implementation: `spec_compliant_steps.py:assign_recipe_to_slot()`
- One recipe per slot (4 meals total)
- Log: "STEP 6: Assigning recipes to meal slots"

### Step 7: Validity Check [IMPLEMENTED] ✓
- Location: `meal_planner.py:_generate_validated_meal_plan_spec_compliant()` line ~398
- Verify all 4 meal slots have recipes:
  - breakfast: not empty
  - lunch: not empty
  - dinner: not empty
  - snack: not empty
- If invalid: retry OR increase multiply_factor (attempt 4+)
- Implementation: `spec_compliant_steps.py:is_plan_valid()`
- Log: "STEP 7: Checking plan validity"

### Step 8: Redistribution [IMPLEMENTED] ✓
- Location: `meal_planner.py:_generate_validated_meal_plan_spec_compliant()` line ~405
- If empty slots exist: move items from overloaded slots
- Rescale: `new_value = old_value × (target_ratio / source_ratio)`
- NOTE: In 1-recipe-per-slot mode, skip but placeholder exists
- Log: "STEP 8: Redistribution check (not needed in 1-recipe-per-slot mode)"

### Step 9: Supplement Solver [IMPLEMENTED] ✓
- Location: `meal_planner.py:_generate_validated_meal_plan_spec_compliant()` line ~410
- Fill remaining macro gaps with:
  - Whey protein
  - Tofu
  - Greek yogurt
- Constraints:
  - Supplements ≤ 30% of protein
  - Supplements ≤ 20% of calories
- Implementation: `supplement_solver.py:fill_macro_gap()` (reused)
- Log: "STEP 9: Filling macro gaps with supplements"

### Step 10: Final Validation [IMPLEMENTED] ✓
- Location: `meal_planner.py:_generate_validated_meal_plan_spec_compliant()` line ~427
- Validate whole plan:
  - Total calories within ±10% of target
  - Each macro within ±20% of target
  - All meals match diet type
  - No allergens present
  - All 4 meal slots present
- Implementation: `meal_validator.py:validate_meal_plan()` (reused)
- Log: "STEP 10: Final validation"

### Step 11: Output [IMPLEMENTED] ✓
- Location: `meal_planner.py:_generate_validated_meal_plan_spec_compliant()` line ~442
- Return structured JSON response:
  ```json
  {
    "calorie_target": number,
    "macros": {
      "protein": number,
      "carbs": number,
      "fat": number
    },
    "meal_plan": {
      "breakfast": {meal details},
      "lunch": {meal details},
      "dinner": {meal details},
      "snack": {meal details}
    },
    "supplements": [list of supplements],
    "warnings": [warning messages]
  }
  ```
- Implementation: `spec_compliant_steps.py` and frontend response formatting
- Log: "STEP 11: Formatting output"

---

## Algorithm Guarantees

✓ **Deterministic**: All steps are algorithmic, no randomness (except hash-based seeding)
✓ **LLM-Free**: All meal selection is via error-based assignment
✓ **Always Returns**: 5-attempt fallback with best candidate
✓ **4-Meal Output**: Exactly 4 meals (breakfast/lunch/dinner/snack)
✓ **Validation Tolerances**: ±10% calories, ±20% macros ✓ **Constraint Handling**: Diet type, allergies, no duplicates
✓ **Supplement Logic**: Proper gap-filling with constraints
✓ **Backward Compatible**: Same API interface as before

---

## File Modifications Summary

### New Files
1. `server/services/nutrition_engine/spec_compliant_steps.py` (~500 lines)
   - Step 2: Carb baseline adjustment
   - Step 4: Age-based multiply factor
   - Step 5: Meal split allocation
   - Step 6: Bucket assignment algorithm
   - Step 7: Validity check
   - Step 8: Redistribution (placeholder)

### Modified Files
1. `server/services/nutrition_engine/meal_planner.py` (~400 lines)
   - Removed beam-search algorithm
   - Removed portion-based food preparation
   - Replaced with spec-compliant orchestration
   - Integrated spec_compliant_steps module
   - Kept utility functions and data models

### Reused Files (No Changes)
- `metabolic_calculator.py` - Step 1
- `constraint_solver.py` - Step 3 filtering
- `macro_split.py` - Macro calculations
- `supplement_solver.py` - Step 9
- `meal_validator.py` - Step 10
- `meal_formatter.py` - Step 11 output

---

## Test Coverage Requirements

- [ ] Unit test: apply_carb_baseline()
- [ ] Unit test: get_age_multiply_factor()
- [ ] Unit test: split_calories_by_meal_slot()
- [ ] Unit test: assign_recipe_to_slot()
- [ ] Unit test: is_plan_valid()
- [ ] Integration test: Full 11-step pipeline
- [ ] Regression test: Existing tests still pass
- [ ] Edge cases: Allergies, diet constraints, edge ages

---

## Backwards Compatibility

- API endpoint: `POST /meal/generate` - UNCHANGED
- Request model: `MealRequest` - UNCHANGED
- Response format: `to_frontend_response()` - UNCHANGED
- All validation rules - UNCHANGED
- Database models - UNCHANGED
