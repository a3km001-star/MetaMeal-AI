import { useState, useEffect } from "react";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import LandingPage from "./components/LandingPage";
import Auth from "./components/Auth";
import Dashboard from "./components/Dashboard";
import MealPlanner from "./components/MealPlanner";
import Insights from "./components/Insights";
import Coach from "./components/Coach";
import WorkoutPlanner from "./components/WorkoutPlanner";

function App() {
  const [user, setUser] = useState(null);
  const [activeView, setActiveView] = useState("dashboard");
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem("darkMode");
    return saved ? JSON.parse(saved) : false;
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    localStorage.setItem("darkMode", JSON.stringify(darkMode));
  }, [darkMode]);

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };

  const handleGetStarted = (mode) => {
    setAuthMode(mode);
    setShowAuth(true);
  };

  const handleLogin = (name) => {
    setUser({ name });
    setShowAuth(false);
    setActiveView("dashboard");
  };

  const handleLogout = () => {
    setUser(null);
    setShowAuth(false);
    setActiveView("dashboard");
  };

  // Show landing page if no user and auth not shown
  if (!user && !showAuth) {
    return (
      <LandingPage
        onGetStarted={handleGetStarted}
        darkMode={darkMode}
        toggleDarkMode={toggleDarkMode}
      />
    );
  }

  // Show auth page if auth is shown
  if (!user && showAuth) {
    return (
      <Auth
        onLogin={handleLogin}
        initialMode={authMode}
        darkMode={darkMode}
        toggleDarkMode={toggleDarkMode}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col transition-colors duration-300">
      <Navbar
        user={user}
        onLogout={handleLogout}
        activeView={activeView}
        setActiveView={setActiveView}
        darkMode={darkMode}
        toggleDarkMode={toggleDarkMode}
      />
      <main className="flex-grow pt-24 md:pt-20 pb-8">
        {activeView === "dashboard" && (
          <Dashboard setActiveView={setActiveView} user={user} />
        )}
        {activeView === "meal-planner" && (
          <MealPlanner setActiveView={setActiveView} />
        )}
        {activeView === "insights" && (
          <Insights setActiveView={setActiveView} />
        )}
        {activeView === "coach" && <Coach setActiveView={setActiveView} />}
        {activeView === "workout-planner" && (
          <WorkoutPlanner setActiveView={setActiveView} />
        )}
      </main>
      <Footer />
    </div>
  );
}

export default App;
