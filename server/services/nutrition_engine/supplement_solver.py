"""Supplement-based macro gap filler for the meal planner.

This module adds small supplement items to an existing meal plan when the food
selection alone cannot meet macro targets, especially protein. Supplements are
meant to fill gaps, not replace core meals.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

SUPPLEMENT_PROTEIN_CAP_RATIO = 0.30
LARGE_PROTEIN_GAP_THRESHOLD = 80.0
CALORIE_CONSISTENCY_TOLERANCE = 15.0
MIN_MEANINGFUL_PROTEIN_GAP = 5.0

_DIET_ALIAS_MAP: Dict[str, str] = {
    "veg": "vegetarian",
    "vegetarian": "vegetarian",
    "non_veg": "non-vegetarian",
    "non-veg": "non-vegetarian",
    "nonveg": "non-vegetarian",
    "non vegetarian": "non-vegetarian",
    "non-vegetarian": "non-vegetarian",
    "vegan": "vegan",
}

_NON_VEG_KEYWORDS = {
    "chicken", "mutton", "lamb", "beef", "pork", "fish", "prawn", "shrimp",
    "meat", "egg", "crab", "lobster", "salmon", "tuna", "anchovy", "bacon",
    "sausage", "ham", "turkey", "duck", "goat",
}
_NON_VEGAN_KEYWORDS = {
    "milk", "curd", "yogurt", "yoghurt", "cheese", "paneer", "cream",
    "butter", "ghee", "dairy", "whey", "casein", "egg", "honey",
}.union(_NON_VEG_KEYWORDS)


def load_supplements() -> List[Dict[str, Any]]:
    """Load the supplement dataset from server/constants/supplements.json."""
    dataset_path = Path(__file__).resolve().parents[2] / "constants" / "supplements.json"

    try:
        with open(dataset_path, "r", encoding="utf-8") as file_handle:
            supplements = json.load(file_handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Supplement dataset not found at {dataset_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("Supplement dataset contains invalid JSON") from exc

    if not isinstance(supplements, list):
        raise ValueError("Supplement dataset must be a list")

    return supplements


def calculate_macro_totals_from_plan(meal_plan: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """Calculate macro totals from a structured raw meal plan."""
    totals = {
        "protein": 0.0,
        "carbohydrates": 0.0,
        "fat": 0.0,
        "calories": 0.0,
    }

    for meal in meal_plan.values():
        totals["protein"] += float(meal.get("protein", 0) or 0)
        totals["carbohydrates"] += float(meal.get("carbs", meal.get("carbohydrates", 0)) or 0)
        totals["fat"] += float(meal.get("fat", 0) or 0)
        totals["calories"] += float(meal.get("calories", 0) or 0)

    return {key: round(value, 2) for key, value in totals.items()}


def detect_macro_gaps(actual_macros: Dict[str, float], target_macros: Dict[str, float]) -> Dict[str, float]:
    """Return non-negative macro gaps between actual totals and targets."""
    return {
        "protein": round(max(0.0, target_macros.get("protein", 0) - actual_macros.get("protein", 0)), 2),
        "carbohydrates": round(
            max(0.0, target_macros.get("carbohydrates", 0) - actual_macros.get("carbohydrates", 0)),
            2,
        ),
        "fat": round(max(0.0, target_macros.get("fat", 0) - actual_macros.get("fat", 0)), 2),
    }


def _contains_keyword(text: str, keyword: str) -> bool:
    return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text.lower()))


def _normalize_diet(diet_type: Optional[str]) -> Optional[str]:
    if not diet_type:
        return None
    normalized = _DIET_ALIAS_MAP.get(diet_type.lower().strip(), diet_type.lower().strip())
    return normalized


def _is_macro_consistent(supplement: Dict[str, Any]) -> bool:
    protein = float(supplement.get("protein", 0) or 0)
    carbs = float(supplement.get("carbs", 0) or 0)
    fat = float(supplement.get("fat", 0) or 0)
    calories = float(supplement.get("calories", 0) or 0)

    if min(protein, carbs, fat, calories) < 0:
        return False

    expected_calories = protein * 4 + carbs * 4 + fat * 9
    return abs(expected_calories - calories) <= CALORIE_CONSISTENCY_TOLERANCE


def _supplement_matches_diet(supplement: Dict[str, Any], user_diet: Optional[str]) -> bool:
    normalized_diet = _normalize_diet(user_diet)
    if not normalized_diet:
        return True

    supplement_diet = _normalize_diet(str(supplement.get("diet_type", "")))
    ingredients = str(supplement.get("ingredients", "")).lower()

    if normalized_diet == "non-vegetarian":
        return True

    if normalized_diet == "vegetarian":
        if supplement_diet == "non-vegetarian":
            return False
        return not any(_contains_keyword(ingredients, keyword) for keyword in _NON_VEG_KEYWORDS)

    if normalized_diet == "vegan":
        if supplement_diet != "vegan":
            return False
        return not any(_contains_keyword(ingredients, keyword) for keyword in _NON_VEGAN_KEYWORDS)

    return True


def _supplement_has_allergen(supplement: Dict[str, Any], allergies: Optional[List[str]]) -> bool:
    if not allergies:
        return False

    ingredients = str(supplement.get("ingredients", "")).lower()
    for allergen in allergies:
        cleaned = allergen.strip().lower()
        if cleaned and _contains_keyword(ingredients, cleaned):
            logger.info("supplement skipped due to allergy: %s contains %s", supplement.get("name", "Unknown"), cleaned)
            return True
    return False


def _select_best_supplement(
    supplements: List[Dict[str, Any]],
    remaining_gap: float,
    remaining_allowance: float,
    remaining_calorie_budget: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    if remaining_allowance <= 0:
        return None

    viable = [
        supplement for supplement in supplements
        if float(supplement.get("protein", 0) or 0) <= remaining_allowance
        and (
            remaining_calorie_budget is None
            or float(supplement.get("calories", 0) or 0) <= remaining_calorie_budget
        )
    ]
    if not viable:
        return None

    target_fill = min(remaining_gap, remaining_allowance)
    return min(
        viable,
        key=lambda supplement: (
            abs(float(supplement.get("protein", 0) or 0) - target_fill),
            float(supplement.get("calories", 0) or 0),
        ),
    )


def fill_macro_gap(
    meal_plan: Dict[str, Dict[str, Any]],
    target_macros: Dict[str, float],
    supplements: List[Dict[str, Any]],
    user_diet: Optional[str] = None,
    allergies: Optional[List[str]] = None,
    target_calories: Optional[float] = None,
    calorie_tolerance: float = 0.10,
) -> Dict[str, Any]:
    """Add supplements to reduce macro gaps while obeying diet and allergy rules.

    Returns a dictionary containing:
    - supplements: selected supplement items
    - macro_gaps: remaining gaps after supplementation
    - updated_totals: macro totals after supplementation
    - warnings: non-fatal warnings
    """
    if not meal_plan:
        raise ValueError("meal_plan cannot be empty")
    if not isinstance(supplements, list):
        raise TypeError("supplements must be a list")

    current_totals = calculate_macro_totals_from_plan(meal_plan)
    macro_gaps = detect_macro_gaps(current_totals, target_macros)
    protein_gap = macro_gaps["protein"]

    warnings: List[str] = []
    selected_supplements: List[Dict[str, Any]] = []

    if protein_gap <= MIN_MEANINGFUL_PROTEIN_GAP:
        return {
            "supplements": selected_supplements,
            "macro_gaps": macro_gaps,
            "updated_totals": current_totals,
            "warnings": warnings,
        }

    logger.info("macro gap detected: protein gap %.2fg", protein_gap)

    if protein_gap > LARGE_PROTEIN_GAP_THRESHOLD:
        warnings.append(
            f"Protein gap is large ({protein_gap:.1f}g); supplementation will be limited."
        )

    filtered_supplements: List[Dict[str, Any]] = []
    for supplement in supplements:
        if not isinstance(supplement, dict):
            continue
        if not _is_macro_consistent(supplement):
            logger.info("supplement skipped due to macro inconsistency: %s", supplement.get("name", "Unknown"))
            continue
        if not _supplement_matches_diet(supplement, user_diet):
            continue
        if _supplement_has_allergen(supplement, allergies):
            continue
        filtered_supplements.append(supplement)

    if not filtered_supplements:
        warnings.append("No supplements allowed for the current diet/allergy constraints.")
        return {
            "supplements": selected_supplements,
            "macro_gaps": macro_gaps,
            "updated_totals": current_totals,
            "warnings": warnings,
        }

    protein_cap = round(float(target_macros.get("protein", 0) or 0) * SUPPLEMENT_PROTEIN_CAP_RATIO, 2)
    added_protein = 0.0
    remaining_gap = protein_gap
    max_total_calories = None
    if target_calories is not None and target_calories > 0:
        max_total_calories = target_calories * (1 + calorie_tolerance)

    while remaining_gap > MIN_MEANINGFUL_PROTEIN_GAP:
        remaining_allowance = protein_cap - added_protein
        remaining_calorie_budget = None
        if max_total_calories is not None:
            remaining_calorie_budget = max_total_calories - current_totals["calories"]
            if remaining_calorie_budget <= 0:
                warnings.append("No calorie headroom left for additional supplements.")
                break

        supplement = _select_best_supplement(
            filtered_supplements,
            remaining_gap,
            remaining_allowance,
            remaining_calorie_budget,
        )
        if supplement is None:
            if remaining_calorie_budget is not None:
                warnings.append("No supplement fits the remaining calorie budget.")
            break

        supplement_item = {
            "name": str(supplement.get("name", "Supplement")),
            "protein": round(float(supplement.get("protein", 0) or 0), 2),
            "carbohydrates": round(float(supplement.get("carbs", 0) or 0), 2),
            "fat": round(float(supplement.get("fat", 0) or 0), 2),
            "calories": round(float(supplement.get("calories", 0) or 0), 2),
            "diet_type": str(supplement.get("diet_type", "Unknown")),
            "ingredients": str(supplement.get("ingredients", "")),
            "instructions": str(supplement.get("instructions", "Consume as directed.")),
        }
        selected_supplements.append(supplement_item)
        logger.info("supplement added: %s", supplement_item["name"])

        added_protein += supplement_item["protein"]
        current_totals["protein"] += supplement_item["protein"]
        current_totals["carbohydrates"] += supplement_item["carbohydrates"]
        current_totals["fat"] += supplement_item["fat"]
        current_totals["calories"] += supplement_item["calories"]
        remaining_gap = max(0.0, target_macros.get("protein", 0) - current_totals["protein"])

    updated_totals = {key: round(value, 2) for key, value in current_totals.items()}
    remaining_gaps = detect_macro_gaps(updated_totals, target_macros)

    if remaining_gaps["protein"] > MIN_MEANINGFUL_PROTEIN_GAP:
        warnings.append(
            f"Protein gap remains after supplementation ({remaining_gaps['protein']:.1f}g)."
        )

    return {
        "supplements": selected_supplements,
        "macro_gaps": remaining_gaps,
        "updated_totals": updated_totals,
        "warnings": warnings,
    }
