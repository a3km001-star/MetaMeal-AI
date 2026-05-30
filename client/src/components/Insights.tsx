import { useState, useEffect } from "react";
import {
  TrendingUp,
  Scale,
  Activity,
  AlertCircle,
  Loader2,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  getWeightHistory,
  getMealHistory,
  getWeeklySummary,
  saveWeight,
} from "../api/meal";

interface WeightEntry {
  date: string;
  weight: number;
}

interface MealEntry {
  date: string;
  calories: number;
}

interface WeeklySummary {
  total_meals_logged: number;
  avg_daily_calories: number;
  consistency_rating: number;
  days_active: number;
}

function Insights() {
  const [weightData, setWeightData] = useState<WeightEntry[]>([]);
  const [mealData, setMealData] = useState<MealEntry[]>([]);
  const [weeklySummary, setWeeklySummary] = useState<WeeklySummary | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [weightInput, setWeightInput] = useState<string>("");
  const [isSavingWeight, setIsSavingWeight] = useState(false);
  const [showWeightInput, setShowWeightInput] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [weightRes, mealRes, summaryRes] = await Promise.all([
          getWeightHistory(),
          getMealHistory(),
          getWeeklySummary(),
        ]);

        setWeightData(weightRes.data?.data || []);
        setMealData(mealRes.data?.data || []);
        setWeeklySummary(summaryRes.data?.data || null);
      } catch (err: any) {
        console.error("Error loading insights data:", err);
        setError(
          err.response?.data?.detail ||
            "Failed to load insights data. Please try again.",
        );
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleSaveWeight = async () => {
    if (!weightInput.trim()) {
      alert("Please enter your weight");
      return;
    }

    const weight = parseFloat(weightInput);
    if (isNaN(weight) || weight <= 0) {
      alert("Please enter a valid weight");
      return;
    }

    setIsSavingWeight(true);
    try {
      const response = await saveWeight(weight);
      const newEntry = response.data?.data;
      setWeightData((prev) => [...prev, newEntry]);
      setWeightInput("");
      setShowWeightInput(false);

      // Notify other components (Profile) that user profile weight changed
      try {
        window.dispatchEvent(
          new CustomEvent("profileUpdated", { detail: { weight } }),
        );
      } catch (e) {
        // ignore dispatch errors
      }

      const storedPrefs = localStorage.getItem("user_preferences");
      if (storedPrefs) {
        try {
          const profilePrefs = JSON.parse(storedPrefs);
          profilePrefs.weight = weight;
          localStorage.setItem(
            "user_preferences",
            JSON.stringify(profilePrefs),
          );
        } catch {
          // ignore local storage parse failures
        }
      }

      alert("Weight updated in your profile");
    } catch (err: any) {
      console.error("Error saving weight:", err);
      alert("Failed to save weight. Please try again.");
    } finally {
      setIsSavingWeight(false);
    }
  };

  // Keep the inline input prefilled with latest weight when data changes
  useEffect(() => {
    const sorted = [...weightData].sort((a, b) => a.date.localeCompare(b.date));
    if (sorted.length) {
      const latest = sorted[sorted.length - 1];
      setWeightInput(String(latest.weight));
    }
  }, [weightData]);

  const sortedWeightData = [...weightData].sort((a, b) =>
    a.date.localeCompare(b.date),
  );
  const chartWeightData = sortedWeightData.slice(-30).map((entry) => ({
    date: entry.date,
    weight: entry.weight,
  }));
  const currentWeight = sortedWeightData.length
    ? sortedWeightData[sortedWeightData.length - 1].weight
    : undefined;

  const chartMealData = mealData.slice(-30).map((entry) => ({
    date: entry.date,
    calories: entry.calories,
  }));

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-300">
            Loading your insights...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
          Insights
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Track your nutrition trends and progress
        </p>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 p-4 rounded-md mb-6 flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 mr-3 mt-0.5" />
          <p className="text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 rounded-2xl p-6 shadow-md border border-blue-200 dark:border-blue-700">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400">
              Total Meals Logged
            </h3>
            <Activity className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <p className="text-4xl font-bold text-blue-900 dark:text-blue-100">
            {weeklySummary?.total_meals_logged || 0}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            Past 7 days
          </p>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/30 rounded-2xl p-6 shadow-md border border-green-200 dark:border-green-700">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400">
              Avg Daily Calories
            </h3>
            <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
          </div>
          <p className="text-4xl font-bold text-green-900 dark:text-green-100">
            {weeklySummary?.avg_daily_calories || 0}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            kcal per day
          </p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/30 dark:to-purple-800/30 rounded-2xl p-6 shadow-md border border-purple-200 dark:border-purple-700">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400">
              Consistency Rating
            </h3>
            <Scale className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          </div>
          <p className="text-4xl font-bold text-purple-900 dark:text-purple-100">
            {weeklySummary?.consistency_rating || 0}%
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            {weeklySummary?.days_active || 0} of 7 days active
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
                  Weight Trend
                </h3>
                {currentWeight !== undefined && (
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Latest weight: {currentWeight.toFixed(1)} kg
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="number"
                  step="0.1"
                  value={weightInput}
                  onChange={(e) => setWeightInput(e.target.value)}
                  placeholder="kg"
                  className="w-24 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={handleSaveWeight}
                  disabled={isSavingWeight}
                  className="text-sm px-3 py-1 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
                >
                  {isSavingWeight ? "Saving..." : "Update"}
                </button>
              </div>
            </div>
          </div>

          {chartWeightData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartWeightData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis
                    dataKey="date"
                    stroke="#999"
                    style={{ fontSize: "12px" }}
                  />
                  <YAxis stroke="#999" style={{ fontSize: "12px" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#f5f5f5",
                      border: "1px solid #ccc",
                      borderRadius: "8px",
                    }}
                    formatter={(value: number) => `${value.toFixed(1)} kg`}
                  />
                  <Line
                    type="monotone"
                    dataKey="weight"
                    stroke="#3b82f6"
                    dot={{ fill: "#3b82f6", r: 4 }}
                    activeDot={{ r: 6 }}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>

              <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                {showWeightInput ? (
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <input
                      type="number"
                      step="0.1"
                      value={weightInput}
                      onChange={(e) => setWeightInput(e.target.value)}
                      placeholder="Enter weight (kg)"
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                    <button
                      onClick={handleSaveWeight}
                      disabled={isSavingWeight}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                    >
                      {isSavingWeight ? "Saving..." : "Save"}
                    </button>
                    <button
                      onClick={() => {
                        setShowWeightInput(false);
                        setWeightInput("");
                      }}
                      className="px-4 py-2 bg-gray-400 text-white rounded-lg hover:bg-gray-500"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div className="text-sm text-gray-600 dark:text-gray-300">
                    Click the Update Weight button above to log a weight entry.
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="h-80 flex items-center justify-center bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="text-center">
                <Scale className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-600 dark:text-gray-300">
                  No weight data yet. Add your first weight entry!
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
              Daily Calories Trend
            </h3>
            <TrendingUp className="w-6 h-6 text-green-500" />
          </div>

          {chartMealData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartMealData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                <XAxis
                  dataKey="date"
                  stroke="#999"
                  style={{ fontSize: "12px" }}
                />
                <YAxis stroke="#999" style={{ fontSize: "12px" }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#f5f5f5",
                    border: "1px solid #ccc",
                    borderRadius: "8px",
                  }}
                  formatter={(value: number) => `${value.toFixed(0)} kcal`}
                />
                <Line
                  type="monotone"
                  dataKey="calories"
                  stroke="#10b981"
                  dot={{ fill: "#10b981", r: 4 }}
                  activeDot={{ r: 6 }}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-80 flex items-center justify-center bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="text-center">
                <Activity className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-600 dark:text-gray-300">
                  No meal data yet. Generate and save meals to see trends!
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}

export default Insights;
