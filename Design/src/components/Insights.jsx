import { TrendingUp, Scale, Activity } from "lucide-react";

function Insights({ setActiveView }) {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
          Insights
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Track your nutrition trends and progress
        </p>
      </div>

      {/* Skeleton Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weight Trend */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
              Weight Trend
            </h3>
            <Scale className="w-6 h-6 text-blue-500" />
          </div>
          <div className="h-48 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 rounded-xl flex items-center justify-center">
            <div className="text-center">
              <div className="animate-pulse">
                <div className="h-32 w-48 bg-blue-200 dark:bg-blue-700/50 rounded-lg mb-4"></div>
              </div>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Loading data...
              </p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-2xl font-bold text-gray-800 dark:text-white">
                --
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Current
              </p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-800 dark:text-white">
                --
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Goal</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-800 dark:text-white">
                --
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Change</p>
            </div>
          </div>
        </div>

        {/* Protein Intake */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
              Protein Intake
            </h3>
            <Activity className="w-6 h-6 text-green-500" />
          </div>
          <div className="h-48 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/30 rounded-xl flex items-center justify-center">
            <div className="text-center">
              <div className="animate-pulse">
                <div className="h-32 w-48 bg-green-200 dark:bg-green-700/50 rounded-lg mb-4"></div>
              </div>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Loading data...
              </p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-2xl font-bold text-gray-800 dark:text-white">
                --
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Avg/Day
              </p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-800 dark:text-white">
                --
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Target</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-800 dark:text-white">
                --
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">% Goal</p>
            </div>
          </div>
        </div>

        {/* Calorie Consistency */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
              Calorie Consistency
            </h3>
            <TrendingUp className="w-6 h-6 text-purple-500" />
          </div>
          <div className="h-48 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/30 dark:to-purple-800/30 rounded-xl flex items-center justify-center">
            <div className="text-center">
              <div className="animate-pulse">
                <div className="h-32 w-48 bg-purple-200 dark:bg-purple-700/50 rounded-lg mb-4"></div>
              </div>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Loading data...
              </p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-2xl font-bold text-gray-800 dark:text-white">
                --
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Streak</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-800 dark:text-white">
                --
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                On Track
              </p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-800 dark:text-white">
                --
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Score</p>
            </div>
          </div>
        </div>
      </div>

      {/* Weekly Summary */}
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-md">
        <h3 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">
          Weekly Summary
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="text-center p-6 bg-gray-50 dark:bg-gray-700 rounded-xl">
            <p className="text-gray-600 dark:text-gray-300 mb-2">
              Total Meals Logged
            </p>
            <p className="text-4xl font-bold text-gray-800 dark:text-white">
              --
            </p>
          </div>
          <div className="text-center p-6 bg-gray-50 dark:bg-gray-700 rounded-xl">
            <p className="text-gray-600 dark:text-gray-300 mb-2">
              Avg Daily Calories
            </p>
            <p className="text-4xl font-bold text-gray-800 dark:text-white">
              --
            </p>
          </div>
          <div className="text-center p-6 bg-gray-50 dark:bg-gray-700 rounded-xl">
            <p className="text-gray-600 dark:text-gray-300 mb-2">
              Macro Balance Score
            </p>
            <p className="text-4xl font-bold text-gray-800 dark:text-white">
              --
            </p>
          </div>
          <div className="text-center p-6 bg-gray-50 dark:bg-gray-700 rounded-xl">
            <p className="text-gray-600 dark:text-gray-300 mb-2">
              Consistency Rating
            </p>
            <p className="text-4xl font-bold text-gray-800 dark:text-white">
              --
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Insights;
