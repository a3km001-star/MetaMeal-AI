import { useEffect, useState } from "react";
import { Dumbbell, Plus, Loader2, Clock, Flame, Target } from "lucide-react";
import { generateWorkoutPlan, getLatestWorkoutPlan } from "../api/workout";

interface WorkoutExercise {
  exercise: string;
  muscle: string;
  sets: number;
  reps: string;
  rest: string;
}

interface WorkoutDay {
  type: string;
  exercises: WorkoutExercise[];
}

const ONE_WEEK_MS = 7 * 24 * 60 * 60 * 1000;

function WorkoutPlanner() {
  const [selectedDay, setSelectedDay] = useState<number>(0);
  const [weeklyPlan, setWeeklyPlan] = useState<Record<
    string,
    WorkoutDay
  > | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [lockExpiresAt, setLockExpiresAt] = useState<Date | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchPlanFromDB = async () => {
      try {
        const response = await getLatestWorkoutPlan();
        const planData = response?.data?.data?.plan;
        if (planData && response.data.data.created_at) {
          const createdAt = new Date(response.data.data.created_at);
          const expiresAt = new Date(createdAt.getTime() + ONE_WEEK_MS);

          if (expiresAt > new Date()) {
            setWeeklyPlan(planData.weekly_plan ?? planData);
            setLockExpiresAt(expiresAt);
          }
        }
      } catch (err) {
        console.error("Failed to fetch workout plan from DB", err);
        // Fallback to localStorage
        const storedPlan = localStorage.getItem("workout_plan");
        const storedGeneratedAt = localStorage.getItem(
          "workout_plan_generated_at",
        );

        if (storedPlan && storedGeneratedAt) {
          const generatedAt = new Date(storedGeneratedAt);
          if (!Number.isNaN(generatedAt.getTime())) {
            const lockUntil = new Date(generatedAt.getTime() + ONE_WEEK_MS);
            if (lockUntil > new Date()) {
              try {
                setWeeklyPlan(JSON.parse(storedPlan));
                setLockExpiresAt(lockUntil);
              } catch {
                localStorage.removeItem("workout_plan");
                localStorage.removeItem("workout_plan_generated_at");
              }
            }
          }
        }
      }
    };

    fetchPlanFromDB();
  }, []);

  const getWorkoutPayload = () => {
    const storedPrefs = localStorage.getItem("user_preferences");
    let preferences = {} as Record<string, any>;

    try {
      preferences = storedPrefs ? JSON.parse(storedPrefs) : {};
    } catch {
      preferences = {};
    }

    const goal = [
      "muscle_gain",
      "fat_loss",
      "maintenance",
      "endurance",
    ].includes(preferences.goal)
      ? preferences.goal
      : "maintenance";

    const activityLevel = preferences.activity_level;
    const experienceLevel =
      activityLevel === "very_active"
        ? "advanced"
        : activityLevel === "moderately_active"
          ? "intermediate"
          : "beginner";

    const weeklyVolume =
      goal === "fat_loss" ? 8 : goal === "muscle_gain" ? 12 : 10;

    return {
      goal,
      experience_level: experienceLevel,
      split: "push_pull_legs",
      training_days: 7,
      weekly_volume_per_muscle: weeklyVolume,
      equipment: "gym",
      injuries: [],
      focus_muscles: [],
    };
  };

  const buildUpcomingDates = () => {
    const today = new Date();
    return Array.from({ length: 7 }, (_, index) => {
      const date = new Date(today);
      date.setHours(0, 0, 0, 0);
      date.setDate(today.getDate() + index);
      return date;
    });
  };

  const formatWeekday = (date: Date) =>
    date.toLocaleDateString(undefined, { weekday: "short" });

  const formatShortDate = (date: Date) =>
    date.toLocaleDateString(undefined, { month: "short", day: "numeric" });

  const formatWorkoutType = (type?: string) => {
    if (!type) {
      return "Not generated";
    }
    return type
      .replace(/_/g, " ")
      .replace(/\b\w/g, (match) => match.toUpperCase());
  };

  const dayDates = buildUpcomingDates();
  const isLocked = Boolean(lockExpiresAt && lockExpiresAt > new Date());
  const selectedDayKey = `day_${selectedDay + 1}`;
  const currentPlan = weeklyPlan ? weeklyPlan[selectedDayKey] : null;
  const isRestDay = currentPlan ? currentPlan.exercises.length === 0 : false;

  const handleGeneratePlan = async () => {
    if (isLocked) {
      return;
    }

    setErrorMessage(null);
    setIsGenerating(true);

    try {
      const payload = getWorkoutPayload();
      const response = await generateWorkoutPlan(payload);
      const plan = response?.data?.data?.weekly_plan as
        | Record<string, WorkoutDay>
        | undefined;

      if (plan) {
        // After generation, fetch the plan from DB to get the lock expiration
        const dbResponse = await getLatestWorkoutPlan();
        if (dbResponse?.data?.data?.created_at) {
          const createdAt = new Date(dbResponse.data.data.created_at);
          const expiresAt = new Date(createdAt.getTime() + ONE_WEEK_MS);
          setLockExpiresAt(expiresAt);
        }

        setWeeklyPlan(plan);
        setSelectedDay(0);
      } else {
        setErrorMessage("Unable to generate workout plan. Please try again.");
      }
    } catch (error: any) {
      setErrorMessage(
        error?.response?.data?.detail?.message ||
          error?.message ||
          "Workout generation failed. Please try again.",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
          Workout Plan Generator
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Generate your personalized 7-day workout schedule. Once generated, the
          plan is locked for one week.
        </p>
      </div>

      {isLocked && lockExpiresAt ? (
        <div className="mb-6 rounded-2xl border border-orange-200 bg-orange-50 dark:border-orange-700 dark:bg-orange-900/40 p-4 text-orange-800 dark:text-orange-100">
          <p className="text-sm font-semibold">Workout generation locked</p>
          <p className="text-sm">
            You last generated a workout plan on{" "}
            {new Date(
              lockExpiresAt.getTime() - ONE_WEEK_MS,
            ).toLocaleDateString()}
            . The next generation unlocks on{" "}
            {lockExpiresAt.toLocaleDateString()}.
          </p>
        </div>
      ) : null}

      {errorMessage ? (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 dark:border-red-700 dark:bg-red-900/40 p-4 text-red-800 dark:text-red-100">
          {errorMessage}
        </div>
      ) : null}

      <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
            Weekly Schedule
          </h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {dayDates.map((date, index) => (
            <button
              key={index}
              onClick={() => setSelectedDay(index)}
              className={`flex flex-col items-center justify-center p-4 rounded-xl transition-all text-left ${
                selectedDay === index
                  ? "bg-gradient-to-br from-orange-500 to-red-600 text-white shadow-lg scale-105"
                  : "bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600"
              }`}
            >
              <span className="text-xs uppercase tracking-wide opacity-80">
                {formatWeekday(date)}
              </span>
              <span className="mt-1 text-sm font-semibold">
                {formatShortDate(date)}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/50 dark:to-orange-800/50 rounded-xl p-6 shadow-md">
          <div className="flex items-center space-x-3">
            <Target className="w-10 h-10 text-orange-600" />
            <div>
              <p className="text-orange-800 dark:text-orange-300 font-semibold text-sm">
                Workout Type
              </p>
              <p className="text-xl font-bold text-orange-600 dark:text-orange-400">
                {formatWorkoutType(currentPlan?.type)}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/50 dark:to-blue-800/50 rounded-xl p-6 shadow-md">
          <div className="flex items-center space-x-3">
            <Clock className="w-10 h-10 text-blue-600" />
            <div>
              <p className="text-blue-800 dark:text-blue-300 font-semibold text-sm">
                Exercises
              </p>
              <p className="text-xl font-bold text-blue-600 dark:text-blue-400">
                {currentPlan ? currentPlan.exercises.length : 0}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/50 dark:to-red-800/50 rounded-xl p-6 shadow-md">
          <div className="flex items-center space-x-3">
            <Flame className="w-10 h-10 text-red-600" />
            <div>
              <p className="text-red-800 dark:text-red-300 font-semibold text-sm">
                Status
              </p>
              <p className="text-xl font-bold text-red-600 dark:text-red-400">
                {currentPlan
                  ? isRestDay
                    ? "Rest Day"
                    : "Workout Day"
                  : "Not Generated"}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md mb-6">
        <h3 className="text-2xl font-bold text-gray-800 dark:text-white mb-6 flex items-center">
          <Dumbbell className="w-6 h-6 mr-2 text-orange-600" />
          {formatWeekday(dayDates[selectedDay])} —{" "}
          {formatShortDate(dayDates[selectedDay])}
        </h3>

        {currentPlan ? (
          currentPlan.exercises.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-8 text-center text-gray-600 dark:text-gray-300">
              <p className="text-lg font-semibold">Rest Day</p>
              <p className="mt-2">
                Take it easy today and recover for tomorrow&apos;s workout.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {currentPlan.exercises.map((exercise, index) => (
                <div
                  key={index}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                >
                  <div className="mb-3 sm:mb-0">
                    <h4 className="text-lg font-semibold text-gray-800 dark:text-white mb-1">
                      {index + 1}. {exercise.exercise}
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      Primary muscle: {exercise.muscle}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-4 text-sm">
                    <div className="text-center">
                      <p className="text-gray-500 dark:text-gray-400 font-medium">
                        Sets
                      </p>
                      <p className="font-semibold text-gray-800 dark:text-white">
                        {exercise.sets}
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-gray-500 dark:text-gray-400 font-medium">
                        Reps
                      </p>
                      <p className="font-semibold text-gray-800 dark:text-white">
                        {exercise.reps}
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-gray-500 dark:text-gray-400 font-medium">
                        Rest
                      </p>
                      <p className="font-semibold text-gray-800 dark:text-white">
                        {exercise.rest}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )
        ) : (
          <div className="rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-8 text-center text-gray-600 dark:text-gray-300">
            <p className="text-lg font-semibold">
              No workout plan generated yet.
            </p>
            <p className="mt-2">
              Click the button below to create a personalized weekly plan and
              lock it for 7 days.
            </p>
          </div>
        )}
      </div>

      <div className="flex flex-col items-center gap-4">
        <button
          onClick={handleGeneratePlan}
          disabled={isLocked || isGenerating}
          className="flex items-center space-x-2 bg-gradient-to-r from-orange-500 to-red-600 text-white px-8 py-4 rounded-xl font-semibold hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Generating...</span>
            </>
          ) : (
            <>
              <Plus className="w-5 h-5" />
              <span>Generate Weekly Workout</span>
            </>
          )}
        </button>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-2xl text-center">
          Workout generation will create a weekly plan once and lock the
          generate button for 7 days.
        </p>
      </div>
    </div>
  );
}

export default WorkoutPlanner;
