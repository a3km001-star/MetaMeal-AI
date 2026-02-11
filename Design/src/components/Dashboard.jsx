import {
  Calendar,
  TrendingUp,
  MessageCircle,
  Utensils,
  Scan,
  Sparkles,
} from "lucide-react";

function Dashboard({ setActiveView, user }) {
  const handleFeatureComingSoon = () => {
    alert("Feature Coming Soon!");
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Hero */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
          Welcome back, {user.name}! 👋
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Let's make today count towards your nutrition goals
        </p>
      </div>

      {/* Streak Card */}
      <div className="mb-8">
        <div className="bg-gradient-to-r from-blue-100 to-indigo-100 dark:from-blue-900/50 dark:to-indigo-900/50 rounded-2xl p-8 shadow-md hover:shadow-lg transition-all">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">
                Current Streak
              </h2>
              <p className="text-5xl font-bold text-blue-600 dark:text-blue-400">
                0 days
              </p>
              <p className="text-gray-600 dark:text-gray-300 mt-2">
                Keep going to build momentum!
              </p>
            </div>
            <Sparkles className="w-24 h-24 text-blue-400 opacity-50" />
          </div>
        </div>
      </div>

      {/* Action Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Generate Meal Plan */}
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

        {/* Analyze Food */}
        <button
          onClick={handleFeatureComingSoon}
          className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-md hover:shadow-2xl hover:scale-105 transition-all text-left group"
        >
          <div className="bg-gradient-to-br from-purple-100 to-pink-100 dark:from-purple-900/50 dark:to-pink-900/50 rounded-full w-16 h-16 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <Scan className="w-8 h-8 text-purple-600" />
          </div>
          <h3 className="text-xl font-bold text-gray-800 dark:text-white mb-2">
            Analyze Food
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            Scan or upload photos of your meals to track nutrition instantly
          </p>
        </button>

        {/* Ask Coach */}
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

      {/* Quick Stats */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Today's Meals
              </p>
              <p className="text-3xl font-bold text-gray-800 dark:text-white">
                3/4
              </p>
            </div>
            <Calendar className="w-12 h-12 text-blue-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Weekly Progress
              </p>
              <p className="text-3xl font-bold text-gray-800 dark:text-white">
                85%
              </p>
            </div>
            <TrendingUp className="w-12 h-12 text-green-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Coach Sessions
              </p>
              <p className="text-3xl font-bold text-gray-800 dark:text-white">
                12
              </p>
            </div>
            <MessageCircle className="w-12 h-12 text-purple-400" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
