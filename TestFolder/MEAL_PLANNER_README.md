# Meal Planner Engine - End-to-End Guide

This document explains how the meal planner works from API request to final JSON response.

## 1. Entry Point and Request Flow

### API Endpoint

- Method: `POST`
- Path: `/meal/generate`
- Router file: `server/routes/meal.py`

### Layered Flow

1. Route receives request payload.
2. Controller validates payload shape and semantic fields.
3. Service generates a deterministic meal plan using constraint-based optimization.
4. Validator checks calories/macros/diet/allergens/structure.
5. Response formatter returns frontend-ready JSON.

## 2. Core Files and Responsibilities

- `server/routes/meal.py`
  - Defines `/meal/generate` endpoint.
- `server/controllers/meal_controller.py`
  - Converts request into validated models and handles API-level errors.
- `server/model/meal_model.py`
  - Request schema validation (`age`, `goal`, `diet_type`, `allergies`, optional `last_meals`).
- `server/services/nutrition_engine/meal_planner.py`
  - Main orchestration logic.
- `server/services/nutrition_engine/spec_compliant_steps.py`
  - Slot targets, scoring, assignment, diversity selection, redistribution, fallback helpers.
- `server/services/nutrition_engine/supplement_solver.py`
  - Fills macro gaps under safety constraints.
- `server/services/nutrition_engine/meal_validator.py`
  - Final pass/fail checks before response.
- `server/services/nutrition_engine/meal_formatter.py`
  - Compact, frontend-safe meal output format.

## 3. Input Contract

Required payload fields:

- `age`
- `sex`
- `height`
- `weight`
- `diet_type`
- `activity_level`
- `goal`
- `allergies`

Optional field:

- `last_meals`
  - Shape: `{ "breakfast": [...], "lunch": [...], "dinner": [...], "snack": [...] }`
  - Used by diversity-aware selection to reduce repeats.

## 4. End-to-End Algorithm

The engine follows a deterministic multi-step pipeline:

1. Metabolic base
   - Calculate BMR and TDEE.
   - Adjust calories by fitness goal.
2. Carb baseline subtraction
   - Subtract fixed `390` kcal from target calories.
3. Filtering
   - Diet filter.
   - Allergy filter.
4. Age-based scaling
   - Scale recipe nutrition using age-based multiply factor.
5. Meal split
   - Split calories/macros into:
     - breakfast `25%`
     - lunch `35%`
     - dinner `30%`
     - snack `10%`
6. Diversity-aware meal selection
   - Score each candidate with:
     - `final_score = error_score + diversity_penalty`
   - Penalties depend on `last_meals` recency.
   - Top-K deterministic pick (quality + variety).
   - Same-day duplicate prevention uses stable recipe IDs.
7. Empty bucket fault tolerance
   - Level 1: redistribution
   - Level 2: borrow from other buckets
   - Level 3: relaxed thresholds (calories/protein)
   - Level 4: snack fallback strategy
   - Level 5: global best match
8. Local swap optimization
   - Improves assignment quality by deterministic slot swaps.
9. Supplement solver
   - Adds supplements if macro gaps remain (diet/allergy aware).
10. Final validation

- Calories, macros, diet, allergens, and structure checks.

11. Output formatting

- Returns stable JSON for frontend.

## 5. Response Contract

Success response:

```json
{
  "success": true,
  "message": "Meal plan generated successfully",
  "data": {
    "calorie_target": 1739.38,
    "macros": {
      "protein": 117.0,
      "carbs": 110.2,
      "fat": 49.0
    },
    "meal_plan": {
      "breakfast": {
        "name": "...",
        "calories": 0,
        "ingredients": "...",
        "instructions": "..."
      },
      "lunch": {
        "name": "...",
        "calories": 0,
        "ingredients": "...",
        "instructions": "..."
      },
      "dinner": {
        "name": "...",
        "calories": 0,
        "ingredients": "...",
        "instructions": "..."
      },
      "snack": {
        "name": "...",
        "calories": 0,
        "ingredients": "...",
        "instructions": "..."
      }
    },
    "supplements": [{ "name": "...", "protein": 0, "calories": 0 }],
    "solver": {
      "mode": "strict | fallback",
      "attempt_count": 1,
      "fallback_reason": null
    },
    "warnings": []
  }
}
```

Notes:

- `meal_plan` is guaranteed as a JSON object with slots in current implementation.
- `solver.mode = fallback` means strict validation did not fully pass and best deterministic candidate was returned.

## 6. Determinism and Diversity Behavior

- No pure random meal selection.
- No unconditional lowest-error only selection.
- Controlled top-k deterministic pick for variety.
- Stable recipe dedup via content-based IDs.
- Hard-repeat blocking is relaxed only when fallback levels are required.

## 7. Running and Testing

From project root:

```bash
E:/FinalYrProject/venv/Scripts/python.exe -m pytest server -q
```

Focused checks:

```bash
E:/FinalYrProject/venv/Scripts/python.exe -m pytest server/test_meal_planner.py -q
E:/FinalYrProject/venv/Scripts/python.exe -m pytest server/test_spec_compliant_implementation.py -q
```

Quick API smoke test:

```bash
E:/FinalYrProject/venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'server'); from fastapi.testclient import TestClient; from app import app; c=TestClient(app); payload={'age':21,'sex':'male','height':165,'weight':65,'diet_type':'non_veg','activity_level':'lightly_active','goal':'fat_loss','allergies':[]}; r=c.post('/meal/generate',json=payload); print(r.status_code); print(r.json())"
```

## 8. Troubleshooting

- If `meal_plan` appears empty, ensure API process is restarted after code changes.
- If many responses are in fallback mode:
  - dataset may not have enough close matches for strict tolerance
  - check logs for calorie/macro validation failures
  - verify diet/allergy filters are not too restrictive
- If repeated meals persist:
  - pass `last_meals` with recent history
  - verify history keys are one of `breakfast/lunch/dinner/snack`

## 9. Production Notes

- Keep this planner deterministic for auditability.
- Log `solver.mode`, `attempt_count`, and warnings for observability.
- Track fallback frequency as a quality KPI.
- Add schedule-level diversity tests when deploying weekly plans.

## 10. Internal Working (Implementation Deep Dive)

This section explains the internal behavior of the engine at function level.

### 10.1 Internal Execution Order

Main orchestrator: `create_meal_plan` -> `_generate_validated_meal_plan_spec_compliant` in `server/services/nutrition_engine/meal_planner.py`.

Per request, internal call order is:

1. `load_food_dataset()`
2. `calculate_bmr(...)`
3. `calculate_tdee(...)`
4. `_adjust_calories_for_goal(...)`
5. `apply_carb_baseline(...)`
6. `calculate_macros(...)`
7. `_prepare_foods_for_profile_spec_compliant(...)`
   - `_normalize_food_for_multiply_factor(...)`
   - `scale_recipe_by_factor(...)`
8. `filter_by_diet(...)`
9. `filter_by_allergies(...)`
10. `split_calories_by_meal_slot(...)`
11. `split_macros_by_meal_slot(...)`
12. `select_meals_with_diversity(...)`
13. `redistribute_empty_slots(...)`
14. `improve_assignment_with_single_slot_swaps(...)`
15. `fill_macro_gap(...)`
16. `_build_complete_meal_plan(...)`
17. `validate_meal_plan(...)`
18. `format_meal_plan(...)` (or fallback reconstruction path)

### 10.2 Internal Data Structures

#### Slot Targets

`slot_macro_targets` (from split step):

```python
{
  "breakfast": {"calories": x, "protein": y, "carbohydrates": z, "fat": w},
  "lunch": {...},
  "dinner": {...},
  "snack": {...}
}
```

#### Selection State

During assignment:

- `assigned_slots: Dict[str, Optional[recipe_dict]]`
- `used_recipe_ids: Set[str]`
  - stable IDs from `_get_stable_recipe_id(...)`
  - avoids same-day duplicates across meal slots

#### History Input

`last_meals` is normalized into:

```python
{
  "breakfast": ["recent meal 1", "recent meal 2", ...],
  "lunch": [...],
  "dinner": [...],
  "snack": [...]
}
```

### 10.3 Scoring Math

Base error per candidate is weighted macro error:

`error_score = 0.60*cal_err + 0.25*protein_err + 0.10*carb_err + 0.05*fat_err`

where each term is normalized absolute error:

`cal_err = abs(target_calories - recipe_calories) / target_calories`

Final ranking score:

`final_score = error_score + diversity_penalty`

Diversity penalty rules:

- `+0.5` if repeated in last 24h (most recent slot history)
- `+0.2` if repeated in recent 1-2 day history
- hard repeat block penalty for same meal appearing in 2 consecutive days
- penalty is scaled down on small candidate pools

### 10.4 Top-K Candidate Selection

The engine does not use pure random choice and does not always pick strict minimum.

Internal steps:

1. Score all valid candidates for a slot.
2. Sort by `(final_score, recipe_name, stable_recipe_id)`.
3. Keep top `k` (`3` to `5`, depending on bucket size).
4. Select one via deterministic hash-based index using:
   - meal type
   - history
   - top candidate IDs

This keeps outputs reproducible while improving diversity.

### 10.5 Fault-Tolerant Fallback Ladder

If any slot is empty, internal fallback levels are applied in order:

1. Redistribution among remaining valid candidates.
2. Borrow from other meal buckets.
3. Relaxed thresholds (`±18%` calories, `±25%` protein).
4. Snack-oriented fallback preference.
5. Global best match regardless of diversity constraints.

At the end, if strict validation still fails, engine returns the best deterministic candidate with:

- `solver.mode = fallback`
- `solver.fallback_reason`
- `warnings[]`

### 10.6 Validation Gate Internals

`validate_meal_plan(...)` is the hard gate before strict success.

Checks:

1. Total calories within tolerance around target.
2. Protein/carbs/fat within macro tolerances.
3. Diet compliance.
4. Allergy compliance.
5. Meal structure validity (all 4 slots and required fields).

If validation fails in an attempt, the planner retries until retry budget is exhausted.

### 10.7 Why Fallback Can Still Be Correct

A fallback response can still be useful and structurally valid when:

- dataset cannot satisfy strict calorie/macro tolerance for the profile
- dietary/allergy filters heavily reduce candidate quality

In such cases, the engine still guarantees output with full meal JSON and supplements, while exposing solver metadata so clients can distinguish strict vs fallback quality.
