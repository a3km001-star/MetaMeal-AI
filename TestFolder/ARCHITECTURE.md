# Meal Planner Architecture Overview

## Request Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Endpoint                           │
│  POST /meal/generate → meal_controller.py                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. INPUT VALIDATION                                              │
│    • MealRequest model validation                                │
│    • Age: 15-100, Weight: 30-300kg, Height: 100-250cm           │
│    • Sex, diet_type, activity_level, goal normalization         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. METABOLIC CALCULATION                                         │
│    metabolic_calculator.py                                      │
│    ├─ BMR: Mifflin-St Jeor equation                              │
│    ├─ TDEE: BMR × activity_level_multiplier                     │
│    └─ Goal Adjustment: ±20%, min 1200F/1500M kcal               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. MACRO CALCULATION                                             │
│    macro_split.py                                               │
│    ├─ Protein: weight_kg × 1.8g/kg (protein-priority)           │
│    ├─ Carbs: Remaining calories × goal_ratio                    │
│    └─ Fat: Remaining calories × goal_ratio                      │
│                                                                  │
│    Goal Ratios:                                                  │
│    • Fat Loss:    40% P / 30% C / 30% F                          │
│    • Muscle Gain: 30% P / 45% C / 25% F                          │
│    • Maintenance: 30% P / 40% C / 30% F                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. DATASET PREPARATION                                           │
│    meal_planner.py:_prepare_foods_for_profile()                 │
│    ├─ Load 500+ recipes from JSON                               │
│    ├─ Scale nutrition: per-100g → age-based portion (85-110g)   │
│    ├─ Create variants: 1.0x, 1.5x, 2.0x, 2.5x, 3.0x            │
│    └─ Sanity check macro values (no outliers)                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. FILTERING                                                     │
│    constraint_solver.py                                         │
│    ├─ filter_by_diet()                                           │
│    │  └─ Remove non-matching diet type (veg/non_veg/vegan)      │
│    └─ filter_by_allergies()                                      │
│       └─ Keyword-based allergen detection                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         ▼
┌─────────────────────────────┐    ┌──────────────────────────────┐
│ 6a. FIRST ATTEMPT           │    │ 6b. FALLBACK ATTEMPTS        │
│ generate_meal_plan()        │    │ (if initial fails)           │
│ • Random + match            │    │ • Macro-aware generation     │
│ • Tolerance: ±10%           │    │ • Beam-search algorithm      │
│ • Quick, good for easy case │    │ • Adaptive tolerance         │
│ • Max attempts: 150         │    │ • Max attempts: 250          │
└─────────────────────────────┘    └──────────────────────────────┘
        │                                         │
        └────────────────┬────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │ BEAM-SEARCH ALGORITHM              │
        │ (Fallback or attempt 4+)           │
        │ ├─ Select top 80 candidate foods   │
        │ ├─ Expand beam state progressively │
        │ ├─ Keep best 250 per depth level   │
        │ ├─ Select best final combination   │
        │ └─ Guaranteed 4-meal output        │
        └────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 7. STRUCTURE PLANNING                                            │
│    _structure_solver_plan()                                      │
│    ├─ Meal 1 → Breakfast                                         │
│    ├─ Meal 2 → Lunch                                             │
│    ├─ Meal 3 → Dinner                                            │
│    └─ Meal 4 → Snack                                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 8. SUPPLEMENT GAP FILLING                                        │
│    supplement_solver.py:fill_macro_gap()                        │
│    ├─ Calculate actual macros from meals                         │
│    ├─ Detect gaps (target - actual)                              │
│    ├─ If protein gap > 5g:                                       │
│    │  ├─ Select diet-compliant supplement                       │
│    │  ├─ Cap at 30% total protein                                │
│    │  └─ Cap at 20% total calories                               │
│    └─ Supplements: Whey / Greek Yogurt / Tofu                    │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 9. VALIDATION                                                    │
│    meal_validator.py:validate_meal_plan()                        │
│    ├─ Calorie check: ±10% of target                              │
│    ├─ Macro checks: ±20% each (protein/carbs/fat)                │
│    ├─ Diet compliance: all meals match diet type                 │
│    ├─ Allergen check: no allergen in any meal                    │
│    └─ If invalid: retry from step 6                              │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
           VALID ✅               INVALID ❌
                │                         │
                │                    Retry
                │                (max 5 attempts)
                │                         │
                └────────────┬────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 10. FORMATTING & RESPONSE                                        │
│     format_meal_plan() + to_frontend_response()                  │
│     ├─ Normalize meal names & fields                             │
│     ├─ Round all numeric values                                  │
│     └─ Return JSON:                                              │
│        {                                                         │
│          "calorie_target": 2000,                                 │
│          "macros": {                                             │
│            "protein": 200,                                       │
│            "carbs": 150,                                         │
│            "fat": 70                                             │
│          },                                                      │
│          "meal_plan": {                                          │
│            "breakfast": {...},                                   │
│            "lunch": {...},                                       │
│            "dinner": {...},                                      │
│            "snack": {...}                                        │
│          },                                                      │
│          "supplements": [{...}],                                 │
│          "warnings": [...]                                       │
│        }                                                         │
└──────────────────────────────────────────────────────────────────┘
```

## Key Modules & Their Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│ meal_planner.py (988 lines)                                     │
│ • Core orchestration (_generate_validated_meal_plan)            │
│ • Regeneration logic (5 attempts with fallback)                 │
│ • Portion scaling & data prep                                   │
│ • Beam-search implementation                                    │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    ┌────────┐    ┌─────────┐    ┌────────┐    ┌──────────┐
    │ Metabolic│  │ Macro   │    │Scoring │    │Structured│
    │Calculator│  │  Split  │    │Function│    │  Plan    │
    ├────────┤    └─────────┘    └────────┘    └──────────┘
    │ BMR    │
    │ TDEE   │
    │ Goal   │
    │ Adjust │
    └────────┘

        UTILITY LAYER
┌─────────────────────────────▬────────────────────────────────┐
│                                                               │
├────────────────┐    ├────────────────┐    ├─────────────────┤
│constraint_     │    │meal_validator  │    │supplement_      │
│solver.py       │    │.py             │    │solver.py        │
│                │    │                │    │                 │
│• Diet filter   │    │• Calorie check │    │• Gap detection  │
│• Allergy       │    │• Macro check   │    │• Supplement     │
│  filter        │    │• Diet          │    │  selection      │
│• Variety check │    │  compliance    │    │• Diet matching  │
│• Meal          │    │• Allergen      │    │• Constraints    │
│  generation    │    │  validation    │    │  application    │
└────────────────┘    └────────────────┘    └─────────────────┘
```

## Data Flow: From Input to Output

```
User Input (JSON)
      │
      ▼
MealRequest ← validation & normalization
      │
      ├─→ UserProfile (internal model)
      │
      ├─→ BMR Calculation
      │   └─→ TDEE
      │       └─→ Calorie Target
      │
      ├─→ Macro Split
      │   └─→ Protein / Carbs / Fat targets
      │
      ├─→ Food Dataset
      │   ├─→ Normalize & scale (per-100g → portion)
      │   ├─→ Create variants
      │   └─→ Filter (diet + allergies)
      │
      ├─→ Meal Selection Algorithm
      │   ├─→ Generate initial plan
      │   ├─→ Fallback 1: Macro-aware
      │   ├─→ Fallback 2: Beam-search
      │   └─→ Validation
      │
      ├─→ Supplement Solving
      │   └─→ Fill macro gaps
      │
      ├─→ Final Validation
      │   └─→ All checks pass?
      │
      └─→ JSON Response (frontend-ready)
```

## Attempt Strategy (5-attempt fallback)

```
ATTEMPT 1
─────────
generate_meal_plan()
├─ Calorie target: 90% of goal
├─ Tolerance: ±10%
└─ Max iterations: 150

    ✅ Valid?
    │
    ├─ NO → Attempt 2
    └─ YES → Return

ATTEMPT 2
─────────
generate_macro_aware_meal_plan()
├─ Calorie target: 87-90% of goal
├─ Protein-focused
├─ Tolerance: ±12-15%
└─ Max iterations: 250

    ✅ Valid?
    │
    ├─ NO → Attempt 3
    └─ YES → Return

ATTEMPT 3
─────────
generate_macro_aware_meal_plan()
├─ Calorie target: 85% of goal
├─ Carb-priority (if vegan)
├─ Tolerance: ±15%
└─ Max iterations: 250

    ✅ Valid?
    │
    ├─ NO → Attempt 4
    └─ YES → Return

ATTEMPT 4 & 5
─────────────
_generate_beam_search_plan()
├─ Calorie target: 88-93% of goal
├─ Beam width: 250 states
├─ Tolerance: ±12-15%
└─ Guaranteed 4 meals

    ✅ Valid?
    │
    ├─ NO → Attempt 5
    └─ YES → Return

NO VALID PLAN AFTER 5 ATTEMPTS
──────────────────────────────
Return best candidate with warnings
└─ "Returned best available plan after retries..."
```

## Error Handling Decision Tree

```
                         Request
                            │
                            ▼
                      Validate Input
                            │
           ┌────────────────┼────────────────┐
           │                │                │
          ❌ INVALID       ✅ VALID          │
           │                │                │
           ▼                │                ▼
    HTTP 400           Continue           Dataset
  "Invalid input"      Generation         Check
           │                │                │
           │                ├────────────┬──┼──┬────────────┐
           │                │            │  │  │            │
           │                └─ Found?    │  │  │         Not Found
           │                    │        │  │  │            │
           │                    ✅       │  │  │            ▼
           │                    │        │  │  │       HTTP 500
           │                    ▼        │  │  │    "Dataset missing"
           │            Run Algorithm    │  │  │
           │              (5 attempts)   │  │  │
           │                    │        │  │  │
           │                    ├─ Pass? ──┴──┤
           │                    │             │
           │                   ✅             ❌
           │                    │             │
           │                    ▼             │
           │           Format Response       │
           │                    │             │
           │                    ▼             ▼
           │              JSON OK       HTTP 400
           │                    │      "No valid plan"
           │                    │
           ├────────────────────┤
           │                    │
           └────────────────────┘
                    │
                    ▼
              Response to Client
```

---

## Summary Statistics

| Metric                | Value     | Notes                        |
| --------------------- | --------- | ---------------------------- |
| Lines of core code    | ~988      | meal_planner.py              |
| Supported meals       | 4         | breakfast/lunch/dinner/snack |
| Regeneration attempts | 5         | with adaptive strategies     |
| Max foods considered  | ~80       | for beam search              |
| Beam width            | 250       | states per depth             |
| Calorie tolerance     | ±10%      | for final validation         |
| Macro tolerance       | ±20%      | per nutrient                 |
| Portion options       | 5         | 1x to 3x multipliers         |
| Supplements           | 3         | whey/yogurt/tofu             |
| Average response time | 200-500ms | estimate                     |
