## 📖 Overview

Every nutrient value is derived from the **Indian Food Composition Tables (IFCT 2017)** — the gold standard government reference for Indian food nutrition — using a transparent, verifiable calculation methodology.

---

## 🗂️ Data Pipeline

### Step 1 — Source Recipe Dataset
- **Source:** [Every Indian Food Dataset (5000+ recipes)](https://www.kaggle.com/datasets/sooryaprakash12/cleaned-indian-recipes-dataset)
- The full dataset contains 5000+ Indian recipes across 7+ cuisine types.
- Trimmed to **Indian, Bengali, and North Indian** cuisine types only → **~1100+ recipes** retained.
- Recipes where one or more ingredients could not be matched in the IFCT dataset were automatically filtered out using **`Remove_the_not_found_recipes.py`** → **~850 recipes** in the final dataset.

### Step 2 — Portion Weight Estimation
- For every ingredient in each recipe, an **approximate educated weight (in grams)** was assigned to represent a **single portion for one person**.
- Example: Milk → 250g, Banana → 70g, Rice → 80g dry weight, etc.
- All weights are **pre-cooking raw weights**, consistent with the IFCT reference standard.
- This forms the **Recipe Dataset**.

### Step 3 — Nutrient Source (IFCT 2017)
- **Source:** [IFCT 2017 Dataset on Kaggle](https://www.kaggle.com/datasets/gijoe707/ifct2017)

> **What is IFCT?**
> The **Indian Food Composition Tables (IFCT 2017)** is a comprehensive nutrient database published by the **National Institute of Nutrition (NIN), India**, under the Indian Council of Medical Research (ICMR). It provides standardized nutrient values per 100g of edible portion for hundreds of raw Indian food ingredients — covering macronutrients, minerals, vitamins, and more. It is the Indian equivalent of the USDA FoodData Central.

- The IFCT dataset was trimmed and filtered to retain only the following **8 key nutritional columns:**

| Nutrient | Unit |
|---|---|
| Calories | kcal |
| Protein | g |
| Fat | g |
| Carbohydrates | g |
| Total Sugar | g |
| Fibre | g |
| Iron | g |
| Calcium | g |

This forms the **Nutrients Dataset**.

### Step 4 — Nutrient Calculation
Nutrient values were computed automatically using the Python script **`recipe_to_nutrition_calculator.py`**, which cross-references each recipe's ingredient weights against the IFCT dataset and applies the following formula for every nutrient:

```
Nutrient Value = (Ingredient Weight in grams / 100) × IFCT Nutrient Value per 100g
```

All nutrient values across all ingredients of a recipe were then **summed** to get the total per-recipe nutrient profile.

### Step 5 — Final Dataset Assembly
- All 8 nutrient totals (Calories, Protein, Fat, Carbs, Sugar, Fibre, Iron, Calcium) were added to the final dataset.
- **Nutrient values are normalized per 100g of the final dish** to make the dataset flexible — since portion sizes vary per individual, per-100g values allow easy scaling to any serving size.
- Additional metadata columns were added:
  - **Meal Type** — `breakfast`, `lunch`, or `snack`
  - **Main Ingredient** — primary ingredient of the dish

---

## ✅ Validation & Accuracy

Two independent validation methods were applied to verify the accuracy of the calculated nutrient values:

### 1. Calorie Formula Check
The standard biochemical formula for total calories was used as a mathematical cross-check:

```
Total Calories = (Protein × 4) + (Carbohydrates × 4) + (Fat × 9)
```

> **Result: < 0.1% average error** across the dataset — confirming internal consistency of the macro calculations.

### 2. Cronometer Verification
A sample of recipes were manually re-entered into **[Cronometer](https://cronometer.com)** (a trusted nutrition tracking tool backed by USDA data) and compared against the MetaMealAi calculated values.

> **Result: ~10% average error** for selected items — within the acceptable range for real-world nutrition data, given natural variance in ingredients across regions, seasons, and sources.

---

## 📊 Dataset Summary

| Property | Value |
|---|---|
| Total Recipes | ~850 (filtered from ~1100+) |
| Cuisine Types | Indian, Bengali, North Indian |
| Portion Basis | Single person, pre-cooking raw weights |
| Nutrient Reference | IFCT 2017 (NIN, ICMR — India) |
| Nutrients Tracked | 8 (Calories, Protein, Fat, Carbs, Sugar, Fibre, Iron, Calcium) |
| Nutrient Unit Basis | Per 100g of final dish |
| Avg. Calorie Error | < 0.1% (formula check) |
| External Validation Error | ~10% (Cronometer spot-check) |

---

## ⚠️ Limitations

- Ingredient weights are **educated estimations** for a typical single portion — not measured from controlled experiments.
- Nutrient values reflect **raw ingredient composition**. Minor changes due to cooking (e.g., water loss, vitamin degradation) are not modelled, though macros and minerals remain largely stable through cooking.
- IFCT values themselves are population averages and may vary by crop variety, region, and season (~5% inherent variance).
- Dataset covers only **3 of 7+ cuisine types** from the original source.

---

## 📚 Sources & Credits

| Resource | Link |
|---|---|
| Original Indian Food Dataset | [Kaggle — sooryaprakash12](https://www.kaggle.com/datasets/sooryaprakash12/cleaned-indian-recipes-dataset) |
| IFCT 2017 Nutrient Data | [Kaggle — gijoe707](https://www.kaggle.com/datasets/gijoe707/ifct2017) |
| External Validation Tool | [Cronometer](https://cronometer.com) |
| IFCT Official Reference | [NIN, ICMR — India](https://www.nin.res.in) |

---

*Built with care for accuracy. Designed for personal nutrition tracking.*
