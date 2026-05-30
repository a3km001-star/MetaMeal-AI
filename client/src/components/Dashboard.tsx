import { useState, useEffect } from "react";
import {
  Calendar,
  TrendingUp,
  MessageCircle,
  Utensils,
  Sparkles,
  Activity,
} from "lucide-react";
import { getMealHistory } from "../api/meal";
import type { User, ViewType } from "../types";

interface DashboardProps {
  setActiveView: (view: ViewType) => void;
  user: User;
}

function Dashboard({ setActiveView, user }: DashboardProps) {
  const displayName = user.name && user.name.trim() ? user.name : "there";
  const [activeDates, setActiveDates] = useState<Set<string>>(new Set());
  const [loadingActivity, setLoadingActivity] = useState(true);
  const [activityError, setActivityError] = useState<string | null>(null);

  const mealGenerationStorageKey = "meal_generation_activity";

  const getStoredMealActivity = (): Set<string> => {
    if (typeof window === "undefined") {
      return new Set();
    }

    try {
      const stored = localStorage.getItem(mealGenerationStorageKey);
      if (!stored) return new Set();
      const parsed = JSON.parse(stored);
      return new Set(
        Array.isArray(parsed)
          ? parsed.filter((item) => typeof item === "string")
          : [],
      );
    } catch {
      return new Set();
    }
  };

  const getCurrentMonthDates = (): string[] => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    const totalDays = new Date(year, month + 1, 0).getDate();
    const monthPrefix = `${year}-${String(month + 1).padStart(2, "0")}-`;
    return Array.from(
      { length: totalDays },
      (_, index) => `${monthPrefix}${String(index + 1).padStart(2, "0")}`,
    );
  };

  const getActiveDatesThisMonth = (): Set<string> => {
    const currentMonth = getCurrentMonthDates();
    const monthSet = new Set(currentMonth);
    return new Set([...activeDates].filter((date) => monthSet.has(date)));
  };

  const computeMaxStreak = (activeSet: Set<string>): number => {
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth();
    const currentDay = today.getDate();
    let maxStreak = 0;
    let streak = 0;

    for (let day = 1; day <= currentDay; day += 1) {
      const dateKey = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      if (activeSet.has(dateKey)) {
        streak += 1;
        maxStreak = Math.max(maxStreak, streak);
      } else {
        streak = 0;
      }
    }

    return maxStreak;
  };

  useEffect(() => {
    const loadActivity = async (): Promise<void> => {
      setLoadingActivity(true);
      setActivityError(null);

      const storedDates = getStoredMealActivity();
      const combinedDates = new Set<string>([...storedDates]);

      try {
        const response = await getMealHistory();
        const history = response.data?.data || [];
        if (Array.isArray(history)) {
          history.forEach((item) => {
            if (item?.date) {
              combinedDates.add(item.date);
            }
          });
        }
      } catch (error: any) {
        console.error(
          "Failed to load meal history for dashboard activity",
          error,
        );
        setActivityError("Could not load meal activity dates.");
      } finally {
        setActiveDates(combinedDates);
        setLoadingActivity(false);
      }
    };

    loadActivity();
  }, []);

  const activeDatesThisMonth = getActiveDatesThisMonth();
  const maxStreak = computeMaxStreak(activeDatesThisMonth);
  const totalDaysThisMonth = getCurrentMonthDates().length;
  const daysPassed = new Date().getDate();
  const skippedDaysCount = Math.max(0, daysPassed - activeDatesThisMonth.size);

  const renderCalendarDay = (
    dateKey: string,
    isFuture: boolean,
  ): JSX.Element => {
    const isActive = activeDatesThisMonth.has(dateKey);
    const dayNumber = Number(dateKey.slice(-2));
    const isToday = dateKey === new Date().toISOString().split("T")[0];

    return (
      <div
        key={dateKey}
        className={`h-10 rounded-2xl border p-1 text-xs font-semibold flex items-center justify-center ${
          isFuture
            ? "bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500"
            : isActive
              ? "bg-emerald-500 text-white"
              : "bg-red-50 dark:bg-red-900/40 text-red-700 dark:text-red-200"
        } ${isToday ? "ring-2 ring-blue-500" : ""}`}
      >
        {dayNumber}
      </div>
    );
  };

  const handleFeatureComingSoon = (): void => {
    alert("Feature Coming Soon!");
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
          Welcome back, {displayName}! 👋
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Let's make today count towards your nutrition goals
        </p>
      </div>

      <div className="mb-8 grid grid-cols-1 xl:grid-cols-[1.8fr_1fr] gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-2xl bg-blue-100 dark:bg-blue-900/30">
                <Calendar className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-800 dark:text-white">
                  Activity Calendar
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Current month — active days are when you generated a meal
                  plan.
                </p>
              </div>
            </div>
            <span className="text-sm text-gray-600 dark:text-gray-300">
              {new Date().toLocaleString("default", { month: "long" })}{" "}
              {new Date().getFullYear()}
            </span>
          </div>

          <div className="grid grid-cols-7 gap-1 text-center text-[10px] uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
              <div key={day} className="font-semibold">
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-0.5">
            {Array.from({
              length: new Date(
                new Date().getFullYear(),
                new Date().getMonth(),
                1,
              ).getDay(),
            }).map((_, index) => (
              <div
                key={`blank-${index}`}
                className="h-10 rounded-2xl bg-transparent"
              ></div>
            ))}
            {getCurrentMonthDates().map((dateKey) => {
              const todayKey = new Date().toISOString().split("T")[0];
              const isFuture = dateKey > todayKey;
              return renderCalendarDay(dateKey, isFuture);
            })}
          </div>

          <div className="mt-4 flex flex-wrap gap-3 text-sm text-gray-600 dark:text-gray-300">
            <div className="inline-flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-emerald-500" /> Active
            </div>
            <div className="inline-flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500" /> Skipped
            </div>
            <div className="inline-flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-gray-300 dark:bg-gray-700" />{" "}
              Future
            </div>
          </div>

          {activityError && (
            <p className="mt-4 text-sm text-red-600 dark:text-red-400">
              {activityError}
            </p>
          )}
        </div>

        <div className="bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/50 dark:to-indigo-900/50 rounded-2xl p-8 shadow-md hover:shadow-lg transition-all">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">
                Monthly streak
              </h2>
              <p className="text-gray-600 dark:text-gray-300">
                Highest consecutive active days this month.
              </p>
            </div>
            <Sparkles className="w-16 h-16 text-blue-400 opacity-60" />
          </div>
          <p className="text-5xl font-bold text-blue-600 dark:text-blue-300 mt-6">
            {loadingActivity ? "..." : `${maxStreak} days`}
          </p>
          <p className="text-gray-600 dark:text-gray-300 mt-3">
            {loadingActivity
              ? "Loading activity..."
              : `${activeDatesThisMonth.size} active days, ${skippedDaysCount} skipped days so far.`}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <button
          onClick={() => setActiveView("meal-planner")}
          className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-md hover:shadow-2xl hover:scale-105 transition-all text-left group"
        >
          <div className="bg-gradient-to-br from-green-100 to-emerald-100 dark:from-green-900/50 dark:to-emerald-900/50 rounded-full w-16 h-16 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <Utensils className="w-8 h-8 text-green-600" />
          </div>
          <h3 className="text-xl font-bold text-gray-800 dark:text-white mb-2">
            Generate Meal Plan
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            Create a personalized meal plan based on your goals and preferences
          </p>
        </button>

        <button
          onClick={() => setActiveView("insights")}
          className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-md hover:shadow-2xl hover:scale-105 transition-all text-left group"
        >
          <div className="bg-gradient-to-br from-purple-100 to-pink-100 dark:from-purple-900/50 dark:to-pink-900/50 rounded-full w-16 h-16 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <TrendingUp className="w-8 h-8 text-purple-600" />
          </div>
          <h3 className="text-xl font-bold text-gray-800 dark:text-white mb-2">
            Insights
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            View your weight, meal and progress trends in one place.
          </p>
        </button>

        <button
          onClick={() => setActiveView("workout-planner")}
          className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-md hover:shadow-2xl hover:scale-105 transition-all text-left group"
        >
          <div className="bg-gradient-to-br from-orange-100 to-amber-100 dark:from-orange-900/50 dark:to-amber-900/50 rounded-full w-16 h-16 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <Activity className="w-8 h-8 text-orange-600" />
          </div>
          <h3 className="text-xl font-bold text-gray-800 dark:text-white mb-2">
            Workout Plan
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            Generate a weekly workout schedule tailored to your goals.
          </p>
        </button>

        <button
          onClick={() => setActiveView("coach")}
          className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-md hover:shadow-2xl hover:scale-105 transition-all text-left group"
        >
          <div className="bg-gradient-to-br from-blue-100 to-cyan-100 dark:from-blue-900/50 dark:to-cyan-900/50 rounded-full w-16 h-16 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <MessageCircle className="w-8 h-8 text-blue-600" />
          </div>
          <h3 className="text-xl font-bold text-gray-800 dark:text-white mb-2">
            Ask Coach
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            Get personalized advice and answers to your nutrition questions
          </p>
        </button>
      </div>
    </div>
  );
}

export default Dashboard;
