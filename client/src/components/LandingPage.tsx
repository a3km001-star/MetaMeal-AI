import {
  Activity,
  TrendingUp,
  Users,
  Award,
  Dumbbell,
  Apple,
  Target,
  Moon,
  Sun,
} from "lucide-react";
import type { AuthMode } from "../types";

interface LandingPageProps {
  onGetStarted: (mode: AuthMode) => void;
  darkMode: boolean;
  toggleDarkMode: () => void;
}

function LandingPage({
  onGetStarted,
  darkMode,
  toggleDarkMode,
}: LandingPageProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors duration-300">
      <header className="fixed top-0 left-0 right-0 bg-white/80 dark:bg-gray-800/80 backdrop-blur-md shadow-sm z-50 transition-colors duration-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg p-2">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold text-gray-800 dark:text-white">
                MetaMeal AI
              </span>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-all"
                aria-label="Toggle dark mode"
              >
                {darkMode ? (
                  <Sun className="w-5 h-5 text-yellow-500" />
                ) : (
                  <Moon className="w-5 h-5 text-gray-700" />
                )}
              </button>
              <button
                onClick={() => onGetStarted("login")}
                className="px-6 py-2 text-blue-600 dark:text-blue-400 font-semibold hover:bg-blue-50 dark:hover:bg-gray-700 rounded-lg transition-all"
              >
                Login
              </button>
              <button
                onClick={() => onGetStarted("register")}
                className="px-6 py-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-semibold rounded-lg hover:shadow-lg hover:scale-105 transition-all"
              >
                Get Started
              </button>
            </div>
          </div>
        </div>
      </header>

      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center">
            <h1 className="text-5xl md:text-7xl font-bold text-gray-900 dark:text-white mb-6">
              Transform Your
              <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                {" "}
                Fitness Journey
              </span>
            </h1>
            <p className="text-xl md:text-2xl text-gray-600 dark:text-gray-300 mb-8 max-w-3xl mx-auto">
              AI-powered nutrition planning, personalized workouts, and expert
              coaching to help you achieve your health goals faster than ever.
            </p>
            <button
              onClick={() => onGetStarted("register")}
              className="px-8 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 text-white text-lg font-semibold rounded-xl hover:shadow-2xl hover:scale-105 transition-all"
            >
              Start Your Free Journey
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-20">
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-lg text-center hover:shadow-xl transition-all">
              <Users className="w-12 h-12 text-blue-600 mx-auto mb-3" />
              <p className="text-3xl font-bold text-gray-800 dark:text-white">
                50K+
              </p>
              <p className="text-gray-600 dark:text-gray-400">Active Users</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-lg text-center hover:shadow-xl transition-all">
              <Target className="w-12 h-12 text-green-600 mx-auto mb-3" />
              <p className="text-3xl font-bold text-gray-800 dark:text-white">
                1M+
              </p>
              <p className="text-gray-600 dark:text-gray-400">Meals Planned</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-lg text-center hover:shadow-xl transition-all">
              <Dumbbell className="w-12 h-12 text-orange-600 mx-auto mb-3" />
              <p className="text-3xl font-bold text-gray-800 dark:text-white">
                500K+
              </p>
              <p className="text-gray-600 dark:text-gray-400">
                Workouts Generated
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-lg text-center hover:shadow-xl transition-all">
              <Award className="w-12 h-12 text-purple-600 mx-auto mb-3" />
              <p className="text-3xl font-bold text-gray-800 dark:text-white">
                98%
              </p>
              <p className="text-gray-600 dark:text-gray-400">Success Rate</p>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 bg-white dark:bg-gray-800 transition-colors duration-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
              Everything You Need to Succeed
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              Powerful features designed to help you reach your fitness goals
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 dark:bg-gradient-to-br dark:from-green-900/30 dark:to-emerald-900/30 rounded-2xl p-8 hover:shadow-xl transition-all">
              <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-full w-16 h-16 flex items-center justify-center mb-6">
                <Apple className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-800 dark:text-white mb-4">
                Smart Meal Planning
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                AI-generated meal plans tailored to your dietary preferences,
                goals, and lifestyle. Track macros effortlessly.
              </p>
            </div>

            <div className="bg-gradient-to-br from-orange-50 to-red-50 dark:bg-gradient-to-br dark:from-orange-900/30 dark:to-red-900/30 rounded-2xl p-8 hover:shadow-xl transition-all">
              <div className="bg-gradient-to-br from-orange-500 to-red-600 rounded-full w-16 h-16 flex items-center justify-center mb-6">
                <Dumbbell className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-800 dark:text-white mb-4">
                Custom Workout Plans
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Personalized 7-day workout schedules based on your fitness
                level, experience, and available equipment.
              </p>
            </div>

            <div className="bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-900/30 dark:to-cyan-900/30 rounded-2xl p-8 hover:shadow-xl transition-all">
              <div className="bg-gradient-to-br from-blue-500 to-cyan-600 rounded-full w-16 h-16 flex items-center justify-center mb-6">
                <TrendingUp className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-800 dark:text-white mb-4">
                Progress Analytics
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Track your journey with detailed insights, weight trends, and
                performance metrics to stay motivated.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 transition-colors duration-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
              Trusted by Thousands
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              Join our growing community of successful fitness enthusiasts
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-lg transition-colors duration-300">
              <div className="flex items-center mb-4">
                <div className="flex text-yellow-400">
                  {[...Array(5)].map((_, i) => (
                    <span key={i} className="text-2xl">
                      ★
                    </span>
                  ))}
                </div>
              </div>
              <p className="text-gray-700 dark:text-gray-300 mb-4 italic">
                "MetaMeal AI completely transformed my approach to nutrition.
                Lost 20 pounds in 3 months!"
              </p>
              <p className="font-semibold text-gray-800 dark:text-white">
                - Sarah M.
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-lg transition-colors duration-300">
              <div className="flex items-center mb-4">
                <div className="flex text-yellow-400">
                  {[...Array(5)].map((_, i) => (
                    <span key={i} className="text-2xl">
                      ★
                    </span>
                  ))}
                </div>
              </div>
              <p className="text-gray-700 dark:text-gray-300 mb-4 italic">
                "The workout plans are incredible. I've gained muscle and feel
                stronger than ever."
              </p>
              <p className="font-semibold text-gray-800 dark:text-white">
                - Mike R.
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-lg transition-colors duration-300">
              <div className="flex items-center mb-4">
                <div className="flex text-yellow-400">
                  {[...Array(5)].map((_, i) => (
                    <span key={i} className="text-2xl">
                      ★
                    </span>
                  ))}
                </div>
              </div>
              <p className="text-gray-700 dark:text-gray-300 mb-4 italic">
                "Best fitness app I've ever used. The AI coach is like having a
                personal trainer!"
              </p>
              <p className="font-semibold text-gray-800 dark:text-white">
                - Emma L.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-700 dark:to-indigo-700 transition-colors duration-300">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Ready to Start Your Journey?
          </h2>
          <p className="text-xl text-blue-100 dark:text-blue-200 mb-8">
            Join thousands of users who have already transformed their lives
          </p>
          <button
            onClick={() => onGetStarted("register")}
            className="px-8 py-4 bg-white dark:bg-gray-100 text-blue-600 text-lg font-semibold rounded-xl hover:shadow-2xl hover:scale-105 transition-all"
          >
            Get Started Free Today
          </button>
        </div>
      </section>

      <footer className="bg-gray-900 dark:bg-black text-gray-300 dark:text-gray-400 py-12 transition-colors duration-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg p-2">
                  <Activity className="w-6 h-6 text-white" />
                </div>
                <span className="text-xl font-bold text-white">
                  MetaMeal AI
                </span>
              </div>
              <p className="text-sm">
                Your complete fitness companion for nutrition and training.
              </p>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <a href="#" className="hover:text-white transition">
                    Features
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition">
                    Pricing
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition">
                    FAQ
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <a href="#" className="hover:text-white transition">
                    About
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition">
                    Blog
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition">
                    Careers
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <a href="#" className="hover:text-white transition">
                    Privacy
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition">
                    Terms
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition">
                    Contact
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-sm">
            <p>&copy; 2025 MetaMeal AI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
