# Metabolic Calculator - FastAPI Usage Examples

## Functions Available

### 1. `calculate_bmr(age, weight, height, sex)`

Calculate Basal Metabolic Rate using Mifflin-St Jeor equation.

### 2. `calculate_tdee(bmr, activity_level)`

Calculate Total Daily Energy Expenditure.

### 3. `adjust_for_goal(tdee, goal)`

Adjust calories based on fitness goal.

### 4. `calculate_complete_metabolic_profile(...)`

Complete calculation combining all three functions.

---

## FastAPI Route Examples

### Basic Endpoint

````python
from fastapi import APIRouter, HTTPException
from services.nutrition_engine.metabolic_calculator import (
    calculate_bmr,
    calculate_tdee,
    adjust_for_goal,
    calculate_complete_metabolic_profile,
    Sex,
    ActivityLevel,
    FitnessGoal,
    MetabolicRequest,
    MetabolicResponse
)

router = APIRouter(prefix="/api/metabolic", tags=["Metabolic Calculator"])


@router.post("/calculate", response_model=MetabolicResponse)
async def calculate_metabolic_profile(request: MetabolicRequest):
    """
    Calculate complete metabolic profile including BMR, TDEE, and target calories.

    Example request:
    ```json
    {
        "age": 25,
        "weight": 70,
        "height": 175,
        "sex": "male",
        "activity_level": "moderately_active",
        "goal": "fat_loss"
    }
    ```
    """
    profile = calculate_complete_metabolic_profile(
        age=request.age,
        weight=request.weight,
        height=request.height,
        sex=request.sex,
        activity_level=request.activity_level,
        goal=request.goal
    )
    return profile


@router.get("/bmr")
async def get_bmr(
    age: int,
    weight: float,
    height: float,
    sex: Sex
):
    """Calculate BMR only."""
    bmr = calculate_bmr(age, weight, height, sex)
    return {
        "bmr": bmr,
        "unit": "kcal/day",
        "formula": "Mifflin-St Jeor"
    }


@router.get("/tdee")
async def get_tdee(
    bmr: float,
    activity_level: ActivityLevel
):
    """Calculate TDEE from BMR."""
    tdee = calculate_tdee(bmr, activity_level)
    return {
        "tdee": tdee,
        "unit": "kcal/day",
        "activity_level": activity_level.value
    }


@router.get("/target-calories")
async def get_target_calories(
    tdee: float,
    goal: FitnessGoal
):
    """Adjust TDEE for fitness goal."""
    target = adjust_for_goal(tdee, goal)
    return {
        "target_calories": target,
        "unit": "kcal/day",
        "goal": goal.value
    }
````

---

## Usage Examples

### Example 1: Calculate BMR

```python
from services.nutrition_engine.metabolic_calculator import calculate_bmr, Sex

# For a 25-year-old male, 70kg, 175cm
bmr = calculate_bmr(
    age=25,
    weight=70.0,
    height=175.0,
    sex=Sex.MALE
)
print(f"BMR: {bmr} kcal/day")
# Output: BMR: 1673.75 kcal/day
```

### Example 2: Calculate TDEE

```python
from services.nutrition_engine.metabolic_calculator import calculate_tdee, ActivityLevel

# Moderately active person with BMR of 1673.75
tdee = calculate_tdee(
    bmr=1673.75,
    activity_level=ActivityLevel.MODERATELY_ACTIVE
)
print(f"TDEE: {tdee} kcal/day")
# Output: TDEE: 2594.31 kcal/day
```

### Example 3: Adjust for Goal

```python
from services.nutrition_engine.metabolic_calculator import adjust_for_goal, FitnessGoal

# Fat loss goal with TDEE of 2594.31
target = adjust_for_goal(
    tdee=2594.31,
    goal=FitnessGoal.FAT_LOSS
)
print(f"Target Calories: {target} kcal/day")
# Output: Target Calories: 2075.45 kcal/day (20% deficit)
```

### Example 4: Complete Profile

```python
from services.nutrition_engine.metabolic_calculator import (
    calculate_complete_metabolic_profile,
    Sex,
    ActivityLevel,
    FitnessGoal
)

profile = calculate_complete_metabolic_profile(
    age=30,
    weight=75.0,
    height=180.0,
    sex=Sex.MALE,
    activity_level=ActivityLevel.VERY_ACTIVE,
    goal=FitnessGoal.MUSCLE_GAIN
)

print(f"BMR: {profile.bmr} kcal/day")
print(f"TDEE: {profile.tdee} kcal/day")
print(f"Target: {profile.target_calories} kcal/day")
print(f"Goal: {profile.goal}")
print(f"Adjustment: {profile.adjustment_percentage}%")
```

---

## Enums Reference

### Sex

- `Sex.MALE` - "male"
- `Sex.FEMALE` - "female"

### ActivityLevel

- `ActivityLevel.SEDENTARY` - "sedentary" (BMR × 1.2)
- `ActivityLevel.LIGHTLY_ACTIVE` - "lightly_active" (BMR × 1.375)
- `ActivityLevel.MODERATELY_ACTIVE` - "moderately_active" (BMR × 1.55)
- `ActivityLevel.VERY_ACTIVE` - "very_active" (BMR × 1.725)

### FitnessGoal

- `FitnessGoal.FAT_LOSS` - "fat_loss" (-20% calories)
- `FitnessGoal.MUSCLE_GAIN` - "muscle_gain" (+10% calories)
- `FitnessGoal.MAINTENANCE` - "maintenance" (0% change)

---

## BMR Formula (Mifflin-St Jeor)

**Men:** BMR = (10 × weight kg) + (6.25 × height cm) - (5 × age) + 5

**Women:** BMR = (10 × weight kg) + (6.25 × height cm) - (5 × age) - 161

---

## Response Schema

```json
{
  "bmr": 1673.75,
  "tdee": 2594.31,
  "target_calories": 2075.45,
  "activity_level": "moderately_active",
  "goal": "fat_loss",
  "adjustment_percentage": -20.0
}
```

---

## Error Handling

All functions raise `HTTPException` with appropriate status codes:

- **400 Bad Request**: Invalid input values (age, weight, height out of range)
- **500 Internal Server Error**: Unexpected calculation errors

Example error response:

```json
{
  "detail": "Weight must be between 30 and 300 kg"
}
```

---

## Test Data Examples

### Fat Loss Example

```python
# 28-year-old female, 65kg, 165cm, moderately active, fat loss
profile = calculate_complete_metabolic_profile(
    age=28, weight=65, height=165, sex=Sex.FEMALE,
    activity_level=ActivityLevel.MODERATELY_ACTIVE,
    goal=FitnessGoal.FAT_LOSS
)
# Result: ~1552 kcal/day target
```

### Muscle Gain Example

```python
# 22-year-old male, 80kg, 185cm, very active, muscle gain
profile = calculate_complete_metabolic_profile(
    age=22, weight=80, height=185, sex=Sex.MALE,
    activity_level=ActivityLevel.VERY_ACTIVE,
    goal=FitnessGoal.MUSCLE_GAIN
)
# Result: ~3100 kcal/day target
```

### Maintenance Example

```python
# 35-year-old female, 60kg, 160cm, lightly active, maintenance
profile = calculate_complete_metabolic_profile(
    age=35, weight=60, height=160, sex=Sex.FEMALE,
    activity_level=ActivityLevel.LIGHTLY_ACTIVE,
    goal=FitnessGoal.MAINTENANCE
)
# Result: ~1700 kcal/day target
```
