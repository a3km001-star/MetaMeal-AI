# Meal Planner Architecture Overview (Current)

This document describes the current implementation of the production meal planner, including internal selection mechanics, fallback guarantees, and response behavior.

## 1. Request to Response Flow

```
POST /meal/generate
    -> routes/meal.py
    -> controllers/meal_controller.py
    -> services/nutrition_engine/meal_planner.py
    -> services/nutrition_engine/meal_validator.py
    -> frontend JSON response
```

## 2. Core Modules

- `server/model/meal_model.py`
  - Validates incoming payload (`age`, `sex`, `height`, `weight`, `diet_type`, `goal`, `allergies`, optional `last_meals`).
- `server/services/nutrition_engine/meal_planner.py`
  - Main orchestration and retry loop.
- `server/services/nutrition_engine/spec_compliant_steps.py`
  - Split targets, weighted error, diversity-aware selection, redistribution, local swap optimization.
- `server/services/nutrition_engine/supplement_solver.py`
  - Macro gap filling with constraints.
- `server/services/nutrition_engine/meal_validator.py`
  - Final calorie/macro/diet/allergy/structure validation.
- `server/services/nutrition_engine/meal_formatter.py`
  - Response shaping for frontend.

## 3. Internal Pipeline (Implemented)

1. Input validation
2. BMR/TDEE and goal-adjusted calories
3. Carb baseline subtraction (`-390 kcal`)
4. Macro target calculation
5. Dataset normalization + age-based scaling
6. Diet/allergy filtering
7. Meal split by slot (`25/35/30/10`)
8. Diversity-aware slot selection
9. Redistribution for empty slots
10. Local swap optimization
11. Supplement solver
12. Final validation
13. Formatting and output

## 4. Diversity-Aware Selection Engine

The engine does not use pure random choice and does not always pick strict minimum error.

### 4.1 Candidate score

For each recipe candidate in a slot:

`final_score = error_score + diversity_penalty`

Where:

- `error_score = 0.60*cal_err + 0.25*protein_err + 0.10*carb_err + 0.05*fat_err`
- `diversity_penalty` is based on recent `last_meals` history.

### 4.2 History penalties

- repeated in last 24h: `+0.5`
- repeated in recent 1-2 day window: `+0.2`
- repeated in 2 consecutive days: hard-block penalty unless fallback requires reuse

### 4.3 Top-K controlled selection

1. Sort by `(final_score, recipe_name, stable_recipe_id)`
2. Keep top `k` (`3` to `5` depending on candidate count)
3. Pick one deterministically from top-k using hash-seeded index

This preserves determinism while improving diversity.

### 4.4 Duplicate prevention

- Same recipe cannot be used in multiple slots on the same day.
- Dedup uses stable content-based recipe IDs (`_get_stable_recipe_id`), not memory addresses.

## 5. Empty Bucket and Fallback Safety

If strict slot fill fails, planner applies deterministic fallback levels:

1. Redistribution
2. Borrowing from other bucket candidate pools
3. Relaxed thresholds (`±18%` calories, `±25%` protein)
4. Snack-oriented fallback candidate strategy
5. Global best match (ignore diversity constraints if needed)

Guarantee: planner always returns a filled meal JSON structure, even in fallback mode.

## 6. Retry Strategy

The planner runs up to 5 attempts:

- Attempts 1-3: strict scale path
- Attempts 4-5: fallback scaling path (`multiply_factor = 2.5`)

If validation still fails after all retries, it returns the best deterministic candidate with warnings and solver metadata.

## 7. Validation Gate (Hard Checks)

`validate_meal_plan(...)` enforces:

- calorie tolerance
- macro tolerances (protein/carbs/fat)
- diet compliance
- allergy compliance
- required meal structure and fields

Strict success requires all checks to pass.

## 8. Response Contract

Successful API envelope:

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

## 9. Determinism Notes

- No unconstrained randomness.
- Stable sorting and stable IDs are used for reproducibility.
- Top-k selection uses deterministic hashing, not non-deterministic RNG.

## 10. Operational Guidance

- Track fallback frequency (`solver.mode == fallback`) as quality KPI.
- Capture warnings and attempt counts in logs/metrics.
- If quality degrades for a cohort, inspect filter strictness and dataset coverage for that cohort.
