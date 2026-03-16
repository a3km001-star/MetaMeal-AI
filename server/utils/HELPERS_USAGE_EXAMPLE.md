# Helper Functions Usage Example

## load_food_dataset() Function

### Basic Usage

```python
from utils.helpers import load_food_dataset, get_food_dataset_metadata

# Load all recipes
recipes = load_food_dataset()
print(f"Loaded {len(recipes)} recipes")

# Access a specific recipe
first_recipe = recipes[0]
print(f"Recipe: {first_recipe['RecipeName']}")
print(f"Calories: {first_recipe['Calories']} kcal")
print(f"Protein: {first_recipe['Protein']} g")
```

### FastAPI Endpoint Example

```python
from fastapi import APIRouter, Query
from utils.helpers import load_food_dataset, get_food_dataset_metadata

router = APIRouter()

@router.get("/recipes")
async def get_all_recipes():
    """Get all available recipes."""
    recipes = load_food_dataset()
    return {
        "total": len(recipes),
        "recipes": recipes
    }

@router.get("/recipes/search")
async def search_recipes(
    max_calories: float = Query(None, description="Maximum calories"),
    min_protein: float = Query(None, description="Minimum protein (g)"),
    diet_type: str = Query(None, description="Diet type filter")
):
    """Search recipes by nutritional criteria."""
    recipes = load_food_dataset()

    # Apply filters with defensive key access and type checking
    filtered = recipes

    if max_calories:
        filtered = [
            r for r in filtered
            if isinstance(r.get('Calories'), (int, float)) and r.get('Calories') <= max_calories
        ]

    if min_protein:
        filtered = [
            r for r in filtered
            if isinstance(r.get('Protein'), (int, float)) and r.get('Protein') >= min_protein
        ]

    if diet_type:
        filtered = [
            r for r in filtered
            if isinstance(r.get('DietType'), str) and r.get('DietType').lower() == diet_type.lower()
        ]

    return {
        "total": len(filtered),
        "recipes": filtered
    }

@router.get("/dataset/info")
async def get_dataset_info():
    """Get dataset metadata information."""
    metadata = get_food_dataset_metadata()
    return metadata
```

### Error Handling

The function automatically raises HTTPException for:

- Missing dataset file (500)
- Invalid JSON format (500)
- Empty dataset (500)
- Other loading errors (500)

FastAPI will automatically handle these exceptions and return appropriate HTTP responses.

### Return Format

Each recipe dictionary contains:

- `RecipeName`: String - Name of the recipe
- `Calories`: Float - Caloric content in kcal
- `Protein`: Float - Protein content in grams
- `Carbohydrates`: Float - Carbohydrate content in grams
- `Fat`: Float - Fat content in grams
- `Ingredients`: String - Comma-separated ingredients list
- `Instructions`: String - Cooking instructions
- `DietType`: String - Dietary classification (e.g., "Unknown", "Vegetarian")

### Performance Note

The function reads from disk each time it's called. For production use, consider:

1. Loading once at startup and caching in memory
2. Using FastAPI's dependency injection with caching
3. Implementing a singleton pattern

Example with caching:

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_cached_food_dataset():
    """Load and cache the food dataset."""
    return load_food_dataset()
```
