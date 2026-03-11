# Diet Type Filtering Guide

The meal planner now supports three diet types with intelligent ingredient-based filtering.

## Supported Diet Types

### 1. **veg** (Vegetarian)

- **What it includes**: Plant-based foods, dairy products (milk, cheese, paneer, curd)
- **What it excludes**: Meat, fish, seafood, eggs
- **Example usage**: `diet_type="veg"`

```python
profile = UserProfile(
    age=25,
    weight=70,
    height=175,
    sex=Sex.MALE,
    activity_level=ActivityLevel.MODERATELY_ACTIVE,
    goal=FitnessGoal.MAINTENANCE,
    diet_type="veg",  # Vegetarian meals only
    allergies=[]
)
```

### 2. **non_veg** (Non-Vegetarian)

- **What it includes**: All foods (vegetarian + non-vegetarian)
- **What it excludes**: Nothing
- **Example usage**: `diet_type="non_veg"`

```python
profile = UserProfile(
    age=30,
    weight=75,
    height=180,
    sex=Sex.MALE,
    activity_level=ActivityLevel.VERY_ACTIVE,
    goal=FitnessGoal.MUSCLE_GAIN,
    diet_type="non_veg",  # All foods allowed
    allergies=[]
)
```

### 3. **vegan**

- **What it includes**: Plant-based foods only
- **What it excludes**: Meat, fish, eggs, dairy (milk, cheese, paneer, curd, butter, ghee, cream)
- **Example usage**: `diet_type="vegan"`

```python
profile = UserProfile(
    age=28,
    weight=65,
    height=170,
    sex=Sex.FEMALE,
    activity_level=ActivityLevel.LIGHTLY_ACTIVE,
    goal=FitnessGoal.FAT_LOSS,
    diet_type="vegan",  # Plant-based only
    allergies=[]
)
```

## Intelligent Filtering

The system uses **intelligent ingredient-based detection** when the dataset doesn't have explicit diet type labels:

### Non-Vegetarian Ingredients Detected:

- chicken, mutton, lamb, beef, pork
- fish, prawn, shrimp, crab, lobster, salmon, tuna
- egg, meat, bacon, sausage, ham, turkey, duck

### Non-Vegan Ingredients Detected:

- All non-vegetarian ingredients (above)
- milk, curd, yogurt, cheese, paneer
- cream, butter, ghee, honey

## Alternative Names

The following aliases are also supported:

- `veg`, `vegetarian` → Vegetarian
- `non_veg`, `non-veg`, `nonveg`, `non vegetarian` → Non-Vegetarian
- `vegan` → Vegan

## Example: Complete Meal Plan Request

```python
from services.nutrition_engine.meal_planner import UserProfile, create_meal_plan
from services.nutrition_engine.metabolic_calculator import Sex, ActivityLevel, FitnessGoal

# Vegetarian user
profile = UserProfile(
    age=25,
    weight=70,
    height=175,
    sex=Sex.MALE,
    activity_level=ActivityLevel.MODERATELY_ACTIVE,
    goal=FitnessGoal.MAINTENANCE,
    diet_type="veg",  # Only vegetarian meals
    allergies=["peanut"]  # Optionally exclude allergens
)

# Generate meal plan
meal_plan = create_meal_plan(profile)

# Result: 4 meals with fixed distribution
# - Breakfast: 25% of daily calories
# - Lunch: 35% of daily calories
# - Dinner: 30% of daily calories
# - Snack: 10% of daily calories
```

## API Usage

When calling the API endpoint:

```json
{
  "age": 25,
  "weight": 70,
  "height": 175,
  "sex": "male",
  "activity_level": "moderately_active",
  "goal": "maintenance",
  "diet_type": "veg",
  "allergies": []
}
```

## Default Behavior

If `diet_type` is not specified or set to `null`, `"any"`, or `"all"`, the system returns meals from all diet categories.
