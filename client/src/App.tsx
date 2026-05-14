import { useState, useEffect } from "react";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import LandingPage from "./pages/LandingPage";
import AuthPage from "./pages/AuthPage";
import { useDarkMode } from "./hooks/useDarkMode";
import { renderActiveView } from "./routes/viewRoutes";
import { getMe } from "./api/auth";
import type { AuthMode, User, ViewType } from "./types";

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [activeView, setActiveView] = useState<ViewType>("dashboard");
  const [showAuth, setShowAuth] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [isInitializing, setIsInitializing] = useState(true);
  const { darkMode, toggleDarkMode } = useDarkMode();

  // Check if user is already logged in on app load
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("token");
      if (token) {
        try {
          const res = await getMe();
          setUser(res.data);
        } catch (error) {
          // Token is invalid or expired
          localStorage.removeItem("token");
        }
      }
      setIsInitializing(false);
    };
    checkAuth();
  }, []);

  const handleGetStarted = (mode: AuthMode): void => {
    setAuthMode(mode);
    setShowAuth(true);
  };

  const handleLogin = (loggedInUser: User): void => {
    setUser(loggedInUser);
    setShowAuth(false);
    setActiveView("dashboard");
  };

  const handleLogout = (): void => {
    localStorage.removeItem("token");
    setUser(null);
    setShowAuth(false);
    setActiveView("dashboard");
  };

  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (!user && !showAuth) {
    return (
      <LandingPage
        onGetStarted={handleGetStarted}
        darkMode={darkMode}
        toggleDarkMode={toggleDarkMode}
      />
    );
  }

  if (!user && showAuth) {
    return (
      <AuthPage
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
        user={user!}
        onLogout={handleLogout}
        activeView={activeView}
        setActiveView={setActiveView}
        darkMode={darkMode}
        toggleDarkMode={toggleDarkMode}
      />
      <main className="flex-grow pt-24 md:pt-20 pb-8">
        {renderActiveView(activeView, { setActiveView, user: user! })}
      </main>
      <Footer />
    </div>
  );
}

export default App;
