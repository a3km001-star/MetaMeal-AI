import { useState } from "react";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import LandingPage from "./pages/LandingPage";
import AuthPage from "./pages/AuthPage";
import { useDarkMode } from "./hooks/useDarkMode";
import { renderActiveView } from "./routes/viewRoutes";
import type { AuthMode, User, ViewType } from "./types";

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [activeView, setActiveView] = useState<ViewType>("dashboard");
  const [showAuth, setShowAuth] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const { darkMode, toggleDarkMode } = useDarkMode();

  const handleGetStarted = (mode: AuthMode): void => {
    setAuthMode(mode);
    setShowAuth(true);
  };

  const handleLogin = (name: string): void => {
    setUser({ name });
    setShowAuth(false);
    setActiveView("dashboard");
  };

  const handleLogout = (): void => {
    setUser(null);
    setShowAuth(false);
    setActiveView("dashboard");
  };

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
