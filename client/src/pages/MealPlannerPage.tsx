import { useState } from "react";
import {
  Utensils,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { generateMealPlan } from "../api/meal";
import type { ViewType } from "../types";

interface MealPlannerProps {
  setActiveView: (view: ViewType) => void;
}

function MealPlanner({ setActiveView }: MealPlannerProps) {
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [mealData, setMealData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedMeal, setExpandedMeal] = useState<string | null>(null); // tracks which card is open

  const handleGeneratePlan = async (): Promise<void> => {
    // 1. Check if profile is complete in local storage
    const stored = localStorage.getItem("user_preferences");
    if (!stored) {
      alert("Please complete your profile first!");
      setActiveView("profile");
      return;
    }

    const profile = JSON.parse(stored);

    // Build payload with ONLY the 9 required MealRequest fields
    // Same payload structure for both authenticated and unauthenticated users
    const payload = {
      age: Number(profile.age),
      sex: String(profile.sex || "male")
        .trim()
        .toLowerCase(),
      height: Number(profile.height),
      weight: Number(profile.weight),
      diet_type: String(profile.diet_type || "non_veg")
        .trim()
        .toLowerCase(),
      activity_level: String(profile.activity_level || "moderately_active")
        .trim()
        .toLowerCase(),
      goal: String(profile.goal || "fat_loss")
        .trim()
        .toLowerCase(),
      allergies: Array.isArray(profile.allergies)
        ? profile.allergies
            .map((item: string) => String(item).trim().toLowerCase())
            .filter(Boolean)
        : [],
      last_meals:
        profile.last_meals && typeof profile.last_meals === "object"
          ? profile.last_meals
          : {},
    };

    if (!payload.age || !payload.weight || !payload.height || !payload.goal) {
      alert(
        "Your profile is missing some required details. Please complete it first!",
      );
      setActiveView("profile");
      return;
    }

    setIsGenerating(true);
    setError(null);
    try {
      console.log("Sending meal generation request:", payload);
      const response = await generateMealPlan(payload);
      console.log("Meal generation response:", response);
      setMealData(response.data.data);
    } catch (err: any) {
      console.error("Meal generation error:", err);
      console.error("Error response:", err.response);
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          JSON.stringify(err.response?.data) ||
          "Failed to generate meal plan. Please try again.",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const toggleExpand = (mealKey: string) => {
    setExpandedMeal(expandedMeal === mealKey ? null : mealKey);
  };

  const renderMacroCard = (
    label: string,
    value: string | number,
    unit: string,
    color: string,
  ) => (
    <div className={`bg-gradient-to-br ${color} rounded-xl p-6 shadow-md`}>
      <p className="font-semibold mb-1 opacity-80">{label}</p>
      <p className="text-3xl font-bold">{value}</p>
      <p className="text-sm opacity-80">{unit}</p>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
            Today's Meal Plan
          </h1>
          <p className="text-gray-600 dark:text-gray-300">
            Fuel your body with optimized nutrition
          </p>
        </div>

        <button
          onClick={handleGeneratePlan}
          disabled={isGenerating}
          className="mt-4 md:mt-0 flex items-center justify-center space-x-2 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-8 py-4 rounded-xl font-semibold hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Analyzing & Generating...</span>
            </>
          ) : (
            <>
              <Utensils className="w-5 h-5" />
              <span>Generate Now</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 p-4 rounded-md mb-6 flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 mr-3 mt-0.5" />
          <p className="text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {isGenerating && (
        <div className="py-20 flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
          <Loader2 className="w-12 h-12 animate-spin text-green-500 mb-4" />
          <p className="text-lg">
            Calculating perfect macros and exploring recipes...
          </p>
          <p className="text-sm opacity-70 mt-2">
            This usually takes 3-10 seconds.
          </p>
        </div>
      )}

      {!isGenerating && mealData && mealData.meal_plan && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Total Macros Section */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 text-gray-800 dark:text-white">
            {renderMacroCard(
              "Target Calories",
              mealData.calorie_target,
              "kcal",
              "from-blue-100 to-blue-200 dark:from-blue-900/40 dark:to-blue-800/40 text-blue-900 dark:text-blue-100",
            )}
            {renderMacroCard(
              "Protein",
              mealData.macros?.protein,
              "grams",
              "from-green-100 to-green-200 dark:from-green-900/40 dark:to-green-800/40 text-green-900 dark:text-green-100",
            )}
            {renderMacroCard(
              "Carbs",
              mealData.macros?.carbs,
              "grams",
              "from-yellow-100 to-yellow-200 dark:from-yellow-900/40 dark:to-yellow-800/40 text-yellow-900 dark:text-yellow-100",
            )}
            {renderMacroCard(
              "Fat",
              mealData.macros?.fat,
              "grams",
              "from-red-100 to-red-200 dark:from-red-900/40 dark:to-red-800/40 text-red-900 dark:text-red-100",
            )}
          </div>

          {/* Individual Meal Cards */}
          <div className="space-y-4 mb-6">
            {["breakfast", "lunch", "dinner", "snack"].map((slot) => {
              const meal = mealData.meal_plan[slot];
              if (!meal) return null;

              const isExpanded = expandedMeal === slot;

              return (
                <div
                  key={slot}
                  className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden transition-all hover:shadow-md"
                >
                  {/* Card Header (Always visible) */}
                  <div
                    onClick={() => toggleExpand(slot)}
                    className="p-6 cursor-pointer flex flex-col lg:flex-row lg:items-center lg:justify-between"
                  >
                    <div className="mb-4 lg:mb-0">
                      <h3 className="text-sm font-bold text-green-600 dark:text-green-400 uppercase tracking-wider mb-1">
                        {slot}
                      </h3>
                      <p className="text-xl font-semibold text-gray-800 dark:text-white">
                        {meal.name}
                      </p>
                    </div>

                    <div className="flex items-center space-x-6 text-sm">
                      <div className="text-center">
                        <p className="text-gray-500">Cal</p>
                        <p className="font-semibold dark:text-white">
                          {meal.calories}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-500">Pro</p>
                        <p className="font-semibold dark:text-white">
                          {meal.protein || "--"}g
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-500">Carbs</p>
                        <p className="font-semibold dark:text-white">
                          {meal.carbs || "--"}g
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-500">Fat</p>
                        <p className="font-semibold dark:text-white">
                          {meal.fat || "--"}g
                        </p>
                      </div>
                      <div className="text-gray-400">
                        {isExpanded ? (
                          <ChevronUp className="w-6 h-6" />
                        ) : (
                          <ChevronDown className="w-6 h-6" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Content (Ingredients & Instructions) */}
                  {isExpanded && (
                    <div className="px-6 pb-6 pt-2 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                        <div>
                          <h4 className="font-semibold text-gray-800 dark:text-white mb-2">
                            Ingredients
                          </h4>
                          <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-line leading-relaxed">
                            {meal.ingredients}
                          </p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-800 dark:text-white mb-2">
                            Instructions
                          </h4>
                          <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-line leading-relaxed">
                            {meal.instructions || "No instructions provided."}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!isGenerating && !mealData && !error && (
        <div className="text-center py-20 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <Utensils className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Ready to plan your day?
          </h2>
          <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            Click the "Generate Now" button above to get a personalized meal
            plan based on your exact profile metrics and goals.
          </p>
        </div>
      )}
    </div>
  );
}

export default MealPlanner;
