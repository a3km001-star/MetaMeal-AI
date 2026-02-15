import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Plus, Loader2 } from "lucide-react";

interface Meal {
  type: string;
  dish: string;
  ingredients: string[];
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
}

function MealPlanner() {
  const [selectedDate, setSelectedDate] = useState<number>(19);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const generateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (generateTimerRef.current) {
        clearTimeout(generateTimerRef.current);
        generateTimerRef.current = null;
      }
    };
  }, []);

  const dates: number[] = [];
  for (let i = 15; i <= 25; i++) {
    dates.push(i);
  }

  const handleGeneratePlan = (): void => {
    setIsGenerating(true);
    if (generateTimerRef.current) {
      clearTimeout(generateTimerRef.current);
    }
    generateTimerRef.current = setTimeout(() => {
      setIsGenerating(false);
      alert("New meal plan generated!");
      generateTimerRef.current = null;
    }, 1500);
  };

  const meals: Meal[] = [
    {
      type: "Breakfast",
      dish: "Greek Yogurt Parfait",
      ingredients: ["Greek yogurt", "Granola", "Berries", "Honey"],
      calories: 450,
      protein: 25,
      carbs: 55,
      fat: 12,
    },
    {
      type: "Lunch",
      dish: "Lamb Rogan Josh",
      ingredients: ["Lamb", "Tomatoes", "Yogurt", "Basmati rice", "Spices"],
      calories: 850,
      protein: 45,
      carbs: 80,
      fat: 35,
    },
    {
      type: "Dinner",
      dish: "Grilled Salmon",
      ingredients: ["Salmon", "Asparagus", "Quinoa", "Lemon", "Olive oil"],
      calories: 680,
      protein: 48,
      carbs: 52,
      fat: 28,
    },
    {
      type: "Snacks",
      dish: "Protein Smoothie",
      ingredients: ["Protein powder", "Banana", "Almond milk", "Peanut butter"],
      calories: 380,
      protein: 32,
      carbs: 38,
      fat: 15,
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
          Meal Planner
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Plan and track your daily nutrition
        </p>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
            December 2025
          </h2>
          <div className="flex space-x-2">
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition">
              <ChevronLeft className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            </button>
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition">
              <ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            </button>
          </div>
        </div>
        <div className="flex space-x-2 overflow-x-auto pb-2">
          {dates.map((date) => (
            <button
              key={date}
              onClick={() => setSelectedDate(date)}
              className={`flex-shrink-0 flex flex-col items-center justify-center w-20 h-24 rounded-xl transition-all ${
                selectedDate === date
                  ? "bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg scale-105"
                  : "bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600"
              }`}
            >
              <span className="text-xs font-medium mb-1">
                {date === 19 ? "Thu" : date === 20 ? "Fri" : "Day"}
              </span>
              <span className="text-2xl font-bold">{date}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/50 dark:to-blue-800/50 rounded-xl p-6 shadow-md">
          <p className="text-blue-800 dark:text-blue-300 font-semibold mb-1">
            Calories
          </p>
          <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">
            2860
          </p>
          <p className="text-sm text-blue-700 dark:text-blue-300">kcal</p>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/50 dark:to-green-800/50 rounded-xl p-6 shadow-md">
          <p className="text-green-800 dark:text-green-300 font-semibold mb-1">
            Protein
          </p>
          <p className="text-3xl font-bold text-green-600 dark:text-green-400">
            160
          </p>
          <p className="text-sm text-green-700 dark:text-green-300">grams</p>
        </div>
        <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-900/50 dark:to-yellow-800/50 rounded-xl p-6 shadow-md">
          <p className="text-yellow-800 dark:text-yellow-300 font-semibold mb-1">
            Carbs
          </p>
          <p className="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
            305
          </p>
          <p className="text-sm text-yellow-700 dark:text-yellow-300">grams</p>
        </div>
        <div className="bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/50 dark:to-red-800/50 rounded-xl p-6 shadow-md">
          <p className="text-red-800 dark:text-red-300 font-semibold mb-1">
            Fat
          </p>
          <p className="text-3xl font-bold text-red-600 dark:text-red-400">
            113
          </p>
          <p className="text-sm text-red-700 dark:text-red-300">grams</p>
        </div>
      </div>

      <div className="space-y-4 mb-6">
        {meals.map((meal, index) => (
          <div
            key={index}
            className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md hover:shadow-lg transition-shadow"
          >
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
              <div className="mb-4 lg:mb-0">
                <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-1">
                  {meal.type}
                </h3>
                <p className="text-xl font-semibold text-gray-700 dark:text-gray-200 mb-2">
                  {meal.dish}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {meal.ingredients.join(" • ")}
                </p>
              </div>
              <div className="flex space-x-4 text-sm">
                <div className="text-center">
                  <p className="text-gray-500 dark:text-gray-400">Cal</p>
                  <p className="font-semibold text-gray-800 dark:text-white">
                    {meal.calories}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-gray-500 dark:text-gray-400">Pro</p>
                  <p className="font-semibold text-gray-800 dark:text-white">
                    {meal.protein}g
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-gray-500 dark:text-gray-400">Carbs</p>
                  <p className="font-semibold text-gray-800 dark:text-white">
                    {meal.carbs}g
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-gray-500 dark:text-gray-400">Fat</p>
                  <p className="font-semibold text-gray-800 dark:text-white">
                    {meal.fat}g
                  </p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-center">
        <button
          onClick={handleGeneratePlan}
          disabled={isGenerating}
          className="flex items-center space-x-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-8 py-4 rounded-xl font-semibold hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Generating...</span>
            </>
          ) : (
            <>
              <Plus className="w-5 h-5" />
              <span>Create New Plan</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default MealPlanner;
