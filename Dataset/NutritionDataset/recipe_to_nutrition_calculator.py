"""
recipe_nutrition.py
--------------------
Matches cleaned ingredients from recipes.csv to nutrition.csv,
scales nutrients by weight (per 100g basis), and outputs a summary CSV.

Matching logic:
  - Each ingredient is scored against every nutrition row.
  - The highest-scoring row(s) are kept.
  - If only one row has the best score → use it directly.
  - If multiple rows share the best score → average their nutrient values,
    then scale by weight as usual.

Usage:
    python recipe_nutrition.py
    python recipe_nutrition.py --nutrition nutrition.csv --recipes recipes.csv --output output.csv
"""

import argparse
import re
import csv
from difflib import SequenceMatcher
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
#  CSV loading
# ─────────────────────────────────────────────────────────────────────────────

def load_csv(path: str):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k.strip(): v.strip() for k, v in row.items()
                         if k is not None and k.strip()})
    return rows


def find_column(row: dict, candidates: list) -> str:
    """
    Find the actual column key by trying each candidate (case-insensitive,
    ignoring spaces). Returns the real key or None.
    """
    normalized = {k.lower().replace(" ", "").replace("(", "").replace(")", ""): k
                  for k in row.keys()}
    for c in candidates:
        key = c.lower().replace(" ", "").replace("(", "").replace(")", "")
        if key in normalized:
            return normalized[key]
    # Substring fallback
    for c in candidates:
        key = c.lower().replace(" ", "")
        for norm_key, orig_key in normalized.items():
            if key in norm_key or norm_key in key:
                return orig_key
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Text normalization & tokenization
# ─────────────────────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[\(\)\[\]\{\}\/\\,;:\"']+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


STOPWORDS = {
    "and", "or", "the", "with", "for", "in", "of", "a", "an",
    "raw", "fresh", "dried", "cooked", "whole", "ground",
    "leaves", "leaf", "seed", "seeds", "sauce", "paste",
    "chopped", "sliced", "diced", "grated", "boiled", "fried",
    "small", "large", "medium", "big", "thinly", "finely",
    "packed", "cup", "cups", "tablespoon", "teaspoon", "inch",
    "piece", "pieces", "handful",
}


def tokenize(text: str) -> list:
    return [w for w in normalize(text).split()
            if len(w) >= 3 and w not in STOPWORDS]


# ─────────────────────────────────────────────────────────────────────────────
#  Matching
# ─────────────────────────────────────────────────────────────────────────────

def score_match(ingredient: str, food_name: str) -> float:
    norm_ing  = normalize(ingredient)
    norm_food = normalize(food_name)

    # Stage 1: exact normalized match
    if norm_ing == norm_food:
        return 1.0

    # Stage 2: substring (only for strings >= 4 chars to avoid "oil"->"boiled")
    if len(norm_ing) >= 4:
        if norm_ing in norm_food:
            return 0.85
        if norm_food in norm_ing:
            return 0.80

    ing_tokens  = tokenize(ingredient)
    food_tokens = tokenize(food_name)

    if not ing_tokens:
        return 0.0

    hits     = set(ing_tokens) & set(food_tokens)
    coverage = len(hits) / len(ing_tokens)

    if coverage == 1.0:
        extra       = max(0, len(food_tokens) - len(ing_tokens))
        token_score = 0.90 - min(0.10, extra * 0.02)
    elif coverage >= 0.5:
        token_score = 0.55 + 0.30 * coverage
    else:
        token_score = 0.0

    # Fuzzy only for longer strings, capped low
    if len(norm_ing) >= 5 and len(norm_food) >= 5:
        seq_score = min(SequenceMatcher(None, norm_ing, norm_food).ratio(), 0.75)
    else:
        seq_score = 0.0

    return max(token_score, seq_score)


def find_best_matches(ingredient: str, nutrition_rows: list,
                      food_col: str, threshold: float = 0.55):
    """
    Returns (candidates, best_score) where candidates is a list of all rows
    that share the single highest match score.
    Returns ([], 0.0) if the best score is below threshold.
    """
    best_score      = 0.0
    best_candidates = []

    for row in nutrition_rows:
        s = score_match(ingredient, row[food_col])
        if s > best_score:
            best_score      = s
            best_candidates = [row]
            if s == 1.0:
                break
        elif s == best_score and s > 0.0:
            best_candidates.append(row)

    if best_score < threshold:
        return [], 0.0

    return best_candidates, best_score


def average_nutrients(candidates: list, col_map: dict) -> dict:
    """
    Given a list of matched nutrition rows and the resolved column map,
    return {canonical_name: averaged_value} across all candidates.
    """
    n = len(candidates)
    return {
        canonical: sum(safe_float(row.get(actual_col, 0)) for row in candidates) / n
        for canonical, actual_col in col_map.items()
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Nutrient column resolution
# ─────────────────────────────────────────────────────────────────────────────

NUTRIENT_ALIASES = {
    "Calories (kcal)":   ["calories (kcal)", "calories", "energy (kcal)", "kcal"],
    "Protein (g)":       ["protein (g)", "protein"],
    "Fat (g)":           ["fat (g)", "fat", "total fat (g)", "total fat"],
    "Carbohydrates (g)": ["carbohydrates (g)", "carbohydrates", "carbs (g)", "carbs"],
    "Total Sugar (g)":   ["total sugar (g)", "total sugar", "sugar (g)", "sugar"],
    "Fibre (g)":         ["fibre (g)", "fibre", "fiber (g)", "fiber", "dietary fibre (g)"],
    "Iron (g)":          ["iron (g)", "iron"],
    "Calcium (g)":       ["calcium (g)", "calcium"],
    "Vitamin D (g)":     ["vitamin d (g)", "vitamin d", "vitamind (g)"],
}


def resolve_nutrient_columns(sample_row: dict) -> dict:
    resolved = {}
    for canonical, aliases in NUTRIENT_ALIASES.items():
        col = find_column(sample_row, aliases)
        if col:
            resolved[canonical] = col
    return resolved


# ─────────────────────────────────────────────────────────────────────────────
#  Core processing
# ─────────────────────────────────────────────────────────────────────────────

def safe_float(val):
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def process_recipes(nutrition_rows, recipe_rows, threshold, min_weight=10.0):

    # ── Detect nutrition CSV columns ───────────────────────────────────────
    nutr_sample = nutrition_rows[0]
    print("\n[Nutrition CSV columns]:", list(nutr_sample.keys()))

    food_col = find_column(nutr_sample, ["Food Name", "FoodName", "food name", "name"])
    if not food_col:
        raise ValueError("Cannot find 'Food Name' column in nutrition CSV. "
                         "Columns found: " + str(list(nutr_sample.keys())))

    col_map = resolve_nutrient_columns(nutr_sample)
    print("\nResolved nutrient columns:")
    for canonical, actual in col_map.items():
        print(f"  '{canonical}' -> '{actual}'")
    missing = [c for c in NUTRIENT_ALIASES if c not in col_map]
    if missing:
        print(f"  [!] Unresolved: {missing}")

    # ── Detect recipe CSV columns ──────────────────────────────────────────
    rec_sample = recipe_rows[0]
    print("\n[Recipe CSV columns]:", list(rec_sample.keys()))

    name_col = find_column(rec_sample, [
        "TranslatedRecipeName", "RecipeName", "recipe name", "name"])
    ing_col  = find_column(rec_sample, [
        "Cleaned-Ingredients", "CleanedIngredients", "cleaned ingredients",
        "ingredients"])
    wt_col   = find_column(rec_sample, [
        "Weights in gms(serially according to cleaned-ingredients)",
        "Weights in gms", "weights in gms", "weights", "weight"])
    cui_col  = find_column(rec_sample, ["Cuisine", "cuisine"])
    time_col = find_column(rec_sample, ["TotalTimeInMins", "total time", "time"])
    cnt_col  = find_column(rec_sample, ["Ingredient-count", "ingredient count",
                                        "ingredientcount"])
    inst_col = find_column(rec_sample, ["TranslatedInstructions", "Translated Instructions",
                                        "instructions", "directions"])

    print(f"\nRecipe columns resolved:")
    print(f"  name      -> '{name_col}'")
    print(f"  ingreds   -> '{ing_col}'")
    print(f"  weights   -> '{wt_col}'")

    if not name_col or not ing_col or not wt_col:
        raise ValueError(
            "Could not find required recipe columns.\n"
            f"  name_col={name_col}, ing_col={ing_col}, wt_col={wt_col}\n"
            f"  Available: {list(rec_sample.keys())}")

    # ── Process each recipe ────────────────────────────────────────────────
    output_rows = []

    for recipe in recipe_rows:
        recipe_name = recipe.get(name_col, "").strip()
        if not recipe_name:
            continue  # skip blank rows

        raw_ing = recipe.get(ing_col, "")
        raw_wt  = recipe.get(wt_col, "")

        ingredients = [i.strip() for i in raw_ing.split(",") if i.strip()]
        wt_parts    = [w.strip() for w in raw_wt.split(",")  if w.strip()]
        weights     = [safe_float(wt_parts[i]) if i < len(wt_parts) else 0.0
                       for i in range(len(ingredients))]

        totals      = defaultdict(float)
        not_found   = []
        total_weight = 0.0  # sum of weights of matched ingredients only

        print(f"\n{'='*65}")
        print(f"Recipe: {recipe_name}")

        for ing, weight in zip(ingredients, weights):
            if weight < min_weight:
                print(f"  [SKIPPED]   '{ing}' (weight={weight}g, below {min_weight}g threshold)")
                continue

            candidates, score = find_best_matches(
                ing, nutrition_rows, food_col, threshold)

            if not candidates:
                not_found.append(ing)
                print(f"  [NOT FOUND] '{ing}' (weight={weight}g)")
                continue

            scale       = weight / 100.0
            num_matches = len(candidates)

            if num_matches == 1:
                # Single best match — use directly
                nutr_values = {
                    canonical: safe_float(candidates[0].get(actual_col, 0))
                    for canonical, actual_col in col_map.items()
                }
                match_label = candidates[0][food_col]
                avg_note    = ""
            else:
                # Multiple tied matches — average all their nutrient values
                nutr_values = average_nutrients(candidates, col_map)
                names       = ", ".join(r[food_col] for r in candidates)
                match_label = f"AVG({num_matches}): {names}"
                avg_note    = f" [averaged {num_matches} tied matches]"

            cal_contrib = 0.0
            for canonical, val in nutr_values.items():
                contrib = val * scale
                totals[canonical] += contrib
                if canonical == "Calories (kcal)":
                    cal_contrib = contrib

            total_weight += weight

            print(f"  [OK] '{ing}' -> '{match_label}' "
                  f"(score={score:.2f}, weight={weight}g, cal+={cal_contrib:.1f}{avg_note})")

        # Normalise all nutrients to per-100g basis
        per100_factor = (100.0 / total_weight) if total_weight > 0 else 0.0

        out = {
            "RecipeName":           recipe_name,
            "Cuisine":              recipe.get(cui_col,  "") if cui_col  else "",
            "TotalTimeInMins":      recipe.get(time_col, "") if time_col else "",
            "IngredientCount":      recipe.get(cnt_col,  "") if cnt_col  else "",
            "Cleaned-Ingredients":  recipe.get(ing_col,  "") if ing_col  else "",
            "Weights":              recipe.get(wt_col,   "") if wt_col   else "",
            "TranslatedInstructions": recipe.get(inst_col, "") if inst_col else "",
        }
        for canonical in NUTRIENT_ALIASES:
            out[canonical] = round(totals.get(canonical, 0.0) * per100_factor, 4)
        out["NotFound"] = " | ".join(not_found) if not_found else ""

        print(f"  -> Calories per 100g: {out['Calories (kcal)']:.1f} kcal "
              f"(total weight used: {total_weight:.0f}g) | "
              f"Not found: {len(not_found)}/{len(ingredients)}")

        output_rows.append(out)

    return output_rows


# ─────────────────────────────────────────────────────────────────────────────
#  Output
# ─────────────────────────────────────────────────────────────────────────────

def write_output(output_rows, path: str):
    if not output_rows:
        print("No rows to write.")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(output_rows[0].keys()))
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"\n[OK] Output written to: {path}")


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nutrition", default="nutrition.csv")
    parser.add_argument("--recipes",   default="recipes.csv")
    parser.add_argument("--output",    default="recipe_nutrition_output.csv")
    parser.add_argument("--threshold",  type=float, default=0.55)
    parser.add_argument("--min-weight", type=float, default=0.0,
                        help="Ingredients below this weight in grams are skipped (default: 10g)")
    args = parser.parse_args()

    print(f"Loading nutrition : {args.nutrition}")
    nutrition_rows = load_csv(args.nutrition)
    print(f"  -> {len(nutrition_rows)} entries")

    print(f"Loading recipes   : {args.recipes}")
    recipe_rows = load_csv(args.recipes)
    print(f"  -> {len(recipe_rows)} entries")

    output_rows = process_recipes(nutrition_rows, recipe_rows, args.threshold, args.min_weight)
    write_output(output_rows, args.output)

    print(f"\nDone: {len(output_rows)} recipes processed.")
    print(f"  Recipes with unmatched ingredients: "
          f"{sum(1 for r in output_rows if r['NotFound'])}")


if __name__ == "__main__":
    main()
