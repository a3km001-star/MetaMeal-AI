import { Activity, LogOut, Moon, Sun, User as UserIcon } from "lucide-react";
import { navItems } from "../routes/navItems";
import type { User, ViewType } from "../types";

interface NavbarProps {
  user: User;
  onLogout: () => void;
  activeView: ViewType;
  setActiveView: (view: ViewType) => void;
  darkMode: boolean;
  toggleDarkMode: () => void;
}

function Navbar({
  user,
  onLogout,
  activeView,
  setActiveView,
  darkMode,
  toggleDarkMode,
}: NavbarProps) {
  return (
    <nav className="fixed top-0 left-0 right-0 bg-white dark:bg-gray-800 shadow-md z-50 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div
            className="flex items-center space-x-2 cursor-pointer"
            onClick={() => setActiveView("dashboard")}
          >
            <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg p-2">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-gray-800 dark:text-white hidden sm:block">
              MetaMeal
            </span>
          </div>

          <div className="hidden md:flex items-center space-x-2">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveView(item.id as ViewType)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all ${
                  activeView === item.id
                    ? "bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-md"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
              >
                <item.icon className="w-4 h-4" />
                <span>{item.name}</span>
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              {darkMode ? (
                <Sun className="w-5 h-5 text-yellow-500" />
              ) : (
                <Moon className="w-5 h-5 text-gray-700" />
              )}
            </button>

            {/* Clickable Profile Button */}
            <button
              onClick={() => setActiveView("profile")}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg font-medium transition-all ${
                activeView === "profile"
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              <UserIcon className="w-4 h-4" />
              <span className="hidden sm:inline">{user.name}</span>
            </button>

            <button
              onClick={onLogout}
              className="flex items-center space-x-2 px-4 py-2 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/50"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
