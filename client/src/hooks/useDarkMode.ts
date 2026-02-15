import { useEffect, useState } from "react";
import { readBoolean, writeBoolean } from "../utils/storage";

const DARK_MODE_KEY = "darkMode";

export const useDarkMode = () => {
  const [darkMode, setDarkMode] = useState<boolean>(() =>
    readBoolean(DARK_MODE_KEY, false),
  );

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    writeBoolean(DARK_MODE_KEY, darkMode);
  }, [darkMode]);

  const toggleDarkMode = (): void => {
    setDarkMode((current) => !current);
  };

  return { darkMode, toggleDarkMode };
};
