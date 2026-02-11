import { useState } from "react";
import { Dumbbell, Plus, Loader2, Clock, Flame, Target } from "lucide-react";

function WorkoutPlanner() {
  const [selectedDay, setSelectedDay] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGeneratePlan = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      alert("New workout plan generated!");
    }, 1500);
  };

  const days = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];

  const workoutPlan = {
    1: {
      focus: "Chest & Triceps",
      duration: "45 min",
      calories: "420 kcal",
      exercises: [
        { name: "Bench Press", sets: "4 sets", reps: "8-12 reps", rest: "90s" },
        {
          name: "Incline Dumbbell Press",
          sets: "3 sets",
          reps: "10-12 reps",
          rest: "60s",
        },
        {
          name: "Cable Flyes",
          sets: "3 sets",
          reps: "12-15 reps",
          rest: "60s",
        },
        {
          name: "Tricep Dips",
          sets: "3 sets",
          reps: "10-12 reps",
          rest: "60s",
        },
        {
          name: "Overhead Tricep Extension",
          sets: "3 sets",
          reps: "12-15 reps",
          rest: "45s",
        },
      ],
    },
    2: {
      focus: "Back & Biceps",
      duration: "50 min",
      calories: "450 kcal",
      exercises: [
        { name: "Deadlifts", sets: "4 sets", reps: "6-8 reps", rest: "120s" },
        { name: "Pull-ups", sets: "3 sets", reps: "8-10 reps", rest: "90s" },
        {
          name: "Barbell Rows",
          sets: "4 sets",
          reps: "8-10 reps",
          rest: "90s",
        },
        {
          name: "Bicep Curls",
          sets: "3 sets",
          reps: "10-12 reps",
          rest: "60s",
        },
        {
          name: "Hammer Curls",
          sets: "3 sets",
          reps: "12-15 reps",
          rest: "45s",
        },
      ],
    },
    3: {
      focus: "Legs & Core",
      duration: "55 min",
      calories: "500 kcal",
      exercises: [
        { name: "Squats", sets: "4 sets", reps: "8-10 reps", rest: "120s" },
        { name: "Leg Press", sets: "3 sets", reps: "10-12 reps", rest: "90s" },
        {
          name: "Romanian Deadlifts",
          sets: "3 sets",
          reps: "10-12 reps",
          rest: "90s",
        },
        { name: "Leg Curls", sets: "3 sets", reps: "12-15 reps", rest: "60s" },
        { name: "Plank", sets: "3 sets", reps: "60s hold", rest: "45s" },
      ],
    },
    4: {
      focus: "Shoulders & Abs",
      duration: "45 min",
      calories: "400 kcal",
      exercises: [
        {
          name: "Military Press",
          sets: "4 sets",
          reps: "8-10 reps",
          rest: "90s",
        },
        {
          name: "Lateral Raises",
          sets: "3 sets",
          reps: "12-15 reps",
          rest: "60s",
        },
        {
          name: "Front Raises",
          sets: "3 sets",
          reps: "12-15 reps",
          rest: "60s",
        },
        {
          name: "Russian Twists",
          sets: "3 sets",
          reps: "20 reps",
          rest: "45s",
        },
        { name: "Mountain Climbers", sets: "3 sets", reps: "30s", rest: "45s" },
      ],
    },
    5: {
      focus: "Full Body Power",
      duration: "50 min",
      calories: "480 kcal",
      exercises: [
        { name: "Power Clean", sets: "4 sets", reps: "5 reps", rest: "120s" },
        {
          name: "Front Squats",
          sets: "4 sets",
          reps: "8-10 reps",
          rest: "90s",
        },
        { name: "Push Press", sets: "3 sets", reps: "8-10 reps", rest: "90s" },
        { name: "Box Jumps", sets: "3 sets", reps: "10 reps", rest: "60s" },
        { name: "Burpees", sets: "3 sets", reps: "15 reps", rest: "60s" },
      ],
    },
    6: {
      focus: "Active Recovery",
      duration: "30 min",
      calories: "200 kcal",
      exercises: [
        { name: "Light Jogging", sets: "1 set", reps: "10 min", rest: "N/A" },
        { name: "Yoga Flow", sets: "1 set", reps: "15 min", rest: "N/A" },
        { name: "Stretching", sets: "1 set", reps: "5 min", rest: "N/A" },
      ],
    },
    7: {
      focus: "Rest Day",
      duration: "0 min",
      calories: "0 kcal",
      exercises: [
        { name: "Complete Rest", sets: "-", reps: "Recovery Day", rest: "N/A" },
      ],
    },
  };

  const currentPlan = workoutPlan[selectedDay];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
          Workout Plan Generator
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Your personalized 7-day workout schedule
        </p>
      </div>

      {/* Day Selector */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
            Select Day
          </h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {days.map((day, index) => (
            <button
              key={index}
              onClick={() => setSelectedDay(index + 1)}
              className={`flex flex-col items-center justify-center p-4 rounded-xl transition-all ${
                selectedDay === index + 1
                  ? "bg-gradient-to-br from-orange-500 to-red-600 text-white shadow-lg scale-105"
                  : "bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600"
              }`}
            >
              <span className="text-xs font-medium mb-1">Day {index + 1}</span>
              <span className="text-sm font-bold">{day.slice(0, 3)}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Workout Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/50 dark:to-orange-800/50 rounded-xl p-6 shadow-md">
          <div className="flex items-center space-x-3">
            <Target className="w-10 h-10 text-orange-600" />
            <div>
              <p className="text-orange-800 dark:text-orange-300 font-semibold text-sm">
                Focus
              </p>
              <p className="text-xl font-bold text-orange-600 dark:text-orange-400">
                {currentPlan.focus}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/50 dark:to-blue-800/50 rounded-xl p-6 shadow-md">
          <div className="flex items-center space-x-3">
            <Clock className="w-10 h-10 text-blue-600" />
            <div>
              <p className="text-blue-800 dark:text-blue-300 font-semibold text-sm">
                Duration
              </p>
              <p className="text-xl font-bold text-blue-600 dark:text-blue-400">
                {currentPlan.duration}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/50 dark:to-red-800/50 rounded-xl p-6 shadow-md">
          <div className="flex items-center space-x-3">
            <Flame className="w-10 h-10 text-red-600" />
            <div>
              <p className="text-red-800 dark:text-red-300 font-semibold text-sm">
                Est. Burn
              </p>
              <p className="text-xl font-bold text-red-600 dark:text-red-400">
                {currentPlan.calories}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Exercise List */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md mb-6">
        <h3 className="text-2xl font-bold text-gray-800 dark:text-white mb-6 flex items-center">
          <Dumbbell className="w-6 h-6 mr-2 text-orange-600" />
          {days[selectedDay - 1]}'s Workout
        </h3>
        <div className="space-y-4">
          {currentPlan.exercises.map((exercise, index) => (
            <div
              key={index}
              className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
            >
              <div className="mb-3 sm:mb-0">
                <h4 className="text-lg font-semibold text-gray-800 dark:text-white mb-1">
                  {index + 1}. {exercise.name}
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  {exercise.sets}
                </p>
              </div>
              <div className="flex space-x-6 text-sm">
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
      </div>

      {/* Generate Button */}
      <div className="flex justify-center">
        <button
          onClick={handleGeneratePlan}
          disabled={isGenerating}
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
              <span>Generate New Workout Plan</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default WorkoutPlanner;
