import { useState, useActionState } from "react";
import { Mail, Lock, User as UserIcon, Moon, Sun } from "lucide-react";
import { registerUser, loginUser, getMe } from "../api/auth";
import type { User } from "../types";

type AuthMode = "login" | "register";

interface AuthProps {
  onLogin: (user: User) => void;
  initialMode?: AuthMode;
  darkMode: boolean;
  toggleDarkMode: () => void;
}

function InputField({
  label,
  icon,
  type = "text",
  value,
  onChange,
  placeholder,
  required,
  minLength,
}: any) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        {label}
      </label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5 pointer-events-none">
          {icon}
        </span>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition"
          placeholder={placeholder}
          required={required}
          minLength={minLength}
        />
      </div>
    </div>
  );
}

function Auth({
  onLogin,
  initialMode = "login",
  darkMode,
  toggleDarkMode,
}: AuthProps) {
  const [isSignIn, setIsSignIn] = useState(initialMode === "login");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoginPending, setIsLoginPending] = useState(false);

  // Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [registerState, registerAction, isRegisterPending] = useActionState(
    async () => {
      if (password !== confirmPassword)
        return { error: "Passwords do not match!", success: false };
      try {
        // 1. Register with only core credentials
        await registerUser({ name, email, password });

        // 2. Login to get token
        const loginRes = await loginUser({ email, password });
        localStorage.setItem("token", loginRes.data.access_token);

        // 3. Get user details from the new /me endpoint
        const meRes = await getMe();
        const user = meRes.data;

        // Sync profile details if they already exist in the database
        if (user.user_details) {
          localStorage.setItem(
            "user_preferences",
            JSON.stringify(user.user_details),
          );
        }

        onLogin(user);
        return { error: null, success: true };
      } catch (error: any) {
        return {
          error:
            error.response?.data?.detail?.[0]?.msg ||
            error.response?.data?.detail ||
            "Registration failed.",
          success: false,
        };
      }
    },
    { error: null, success: false },
  );

  async function handleSignIn(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoginError(null);
    setIsLoginPending(true);
    try {
      const res = await loginUser({ email, password });
      localStorage.setItem("token", res.data.access_token);

      const meRes = await getMe();
      const user = meRes.data;

      // Sync profile details if they already exist in the database
      if (user.user_details) {
        localStorage.setItem(
          "user_preferences",
          JSON.stringify(user.user_details),
        );
      }

      onLogin(user);
    } catch (error: any) {
      setLoginError(
        error.response?.data?.detail || "Invalid email or password",
      );
    } finally {
      setIsLoginPending(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md p-8 relative">
        <button
          onClick={toggleDarkMode}
          className="absolute top-4 right-4 p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200"
        >
          {darkMode ? (
            <Sun className="w-5 h-5 text-yellow-500" />
          ) : (
            <Moon className="w-5 h-5 text-gray-700" />
          )}
        </button>

        <div className="flex justify-center mb-6">
          <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full p-4">
            <UserIcon className="w-8 h-8 text-white" />
          </div>
        </div>

        <h1 className="text-3xl font-bold text-center text-gray-800 dark:text-white mb-2">
          Welcome
        </h1>

        <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1 mb-6 mt-6">
          <button
            onClick={() => setIsSignIn(true)}
            className={`flex-1 py-2 px-4 rounded-md font-medium transition-all ${isSignIn ? "bg-white dark:bg-gray-600 text-blue-600 dark:text-white shadow-sm" : "text-gray-600 dark:text-gray-300"}`}
          >
            Sign In
          </button>
          <button
            onClick={() => setIsSignIn(false)}
            className={`flex-1 py-2 px-4 rounded-md font-medium transition-all ${!isSignIn ? "bg-white dark:bg-gray-600 text-blue-600 dark:text-white shadow-sm" : "text-gray-600 dark:text-gray-300"}`}
          >
            Register
          </button>
        </div>

        {isSignIn ? (
          <form onSubmit={handleSignIn} className="space-y-4">
            {loginError && (
              <p className="text-red-500 text-sm text-center">{loginError}</p>
            )}
            <InputField
              label="Email"
              icon={<Mail className="w-5 h-5" />}
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="Email"
              required
            />
            <InputField
              label="Password"
              icon={<Lock className="w-5 h-5" />}
              type="password"
              value={password}
              onChange={setPassword}
              placeholder="Password"
              required
              minLength={6}
            />
            <button
              type="submit"
              disabled={isLoginPending}
              className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 rounded-lg font-semibold hover:shadow-lg transition-all disabled:opacity-60"
            >
              {isLoginPending ? "Signing in..." : "Sign In"}
            </button>
          </form>
        ) : (
          <form action={registerAction} className="space-y-4">
            {registerState.error && (
              <p className="text-red-500 text-sm text-center">
                {registerState.error}
              </p>
            )}
            <InputField
              label="Full Name"
              icon={<UserIcon className="w-5 h-5" />}
              value={name}
              onChange={setName}
              placeholder="Full name"
              required
            />
            <InputField
              label="Email"
              icon={<Mail className="w-5 h-5" />}
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="Email"
              required
            />
            <InputField
              label="Password"
              icon={<Lock className="w-5 h-5" />}
              type="password"
              value={password}
              onChange={setPassword}
              placeholder="Password"
              required
              minLength={8}
            />
            <InputField
              label="Confirm Password"
              icon={<Lock className="w-5 h-5" />}
              type="password"
              value={confirmPassword}
              onChange={setConfirmPassword}
              placeholder="Confirm password"
              required
              minLength={8}
            />

            <button
              type="submit"
              disabled={isRegisterPending}
              className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 rounded-lg font-semibold hover:shadow-lg transition-all disabled:opacity-60"
            >
              {isRegisterPending ? "Creating Account..." : "Create Account"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default Auth;
