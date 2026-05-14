import { useState, useEffect } from "react";
import { User, Scale, Ruler, Calendar, CheckCircle2 } from "lucide-react";
import { getMe } from "../api/auth";
import type { UserProfileData } from "../types";

function Profile() {
  const [profile, setProfile] = useState<UserProfileData>({
    age: undefined,
    height: undefined,
    weight: undefined,
    sex: "male",
    activity_level: "moderately_active",
    goal: "fat_loss",
    diet_type: "non_veg",
    allergies: [],
  });
  const [saved, setSaved] = useState(false);
  const [allergiesText, setAllergiesText] = useState("");

  useEffect(() => {
    const fetchProfileData = async () => {
      try {
        // 1. Try to get the latest profile from the database
        const res = await getMe();
        if (res.data.user_details) {
          setProfile(res.data.user_details);
          if (res.data.user_details.allergies) {
            setAllergiesText(res.data.user_details.allergies.join(", "));
          }
          // Sync it locally just in case
          localStorage.setItem(
            "user_preferences",
            JSON.stringify(res.data.user_details),
          );
          return; // Exit early since we got fresh data
        }
      } catch (err) {
        console.error("Could not fetch profile from DB", err);
      }

      // 2. Fallback to local storage if DB fetch failed or user_details is empty
      const stored = localStorage.getItem("user_preferences");
      if (stored) {
        const parsed = JSON.parse(stored);
        setProfile(parsed);
        if (parsed.allergies) {
          setAllergiesText(parsed.allergies.join(", "));
        }
      }
    };

    fetchProfileData();
  }, []);

  const handleChange = (field: keyof UserProfileData, value: any) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const updatedProfile = {
      ...profile,
      allergies: allergiesText
        .split(",")
        .map((a) => a.trim())
        .filter((a) => a.length > 0),
    };

    // Ensure numeric fields are actually numbers
    if (updatedProfile.age) updatedProfile.age = Number(updatedProfile.age);
    if (updatedProfile.height)
      updatedProfile.height = Number(updatedProfile.height);
    if (updatedProfile.weight)
      updatedProfile.weight = Number(updatedProfile.weight);

    // Save locally. The actual DB save happens when they call /meal/generate
    localStorage.setItem("user_preferences", JSON.stringify(updatedProfile));
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-md">
        <div className="flex items-center space-x-4 mb-8">
          <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full p-3">
            <User className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
              Your Profile
            </h1>
            <p className="text-gray-600 dark:text-gray-300">
              Complete this to generate accurate meal & workout plans.
            </p>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Age
              </label>
              <div className="relative">
                <Calendar className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                <input
                  type="number"
                  required
                  value={profile.age || ""}
                  onChange={(e) => handleChange("age", e.target.value)}
                  className="w-full pl-10 p-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Biological Sex
              </label>
              <select
                required
                value={profile.sex}
                onChange={(e) => handleChange("sex", e.target.value)}
                className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Height (cm)
              </label>
              <div className="relative">
                <Ruler className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                <input
                  type="number"
                  required
                  value={profile.height || ""}
                  onChange={(e) => handleChange("height", e.target.value)}
                  className="w-full pl-10 p-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Weight (kg)
              </label>
              <div className="relative">
                <Scale className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                <input
                  type="number"
                  step="0.1"
                  required
                  value={profile.weight || ""}
                  onChange={(e) => handleChange("weight", e.target.value)}
                  className="w-full pl-10 p-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Fitness Goal
              </label>
              <select
                required
                value={profile.goal}
                onChange={(e) => handleChange("goal", e.target.value)}
                className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="fat_loss">Fat Loss</option>
                <option value="muscle_gain">Muscle Gain</option>
                <option value="maintenance">Maintenance</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Activity Level
              </label>
              <select
                required
                value={profile.activity_level}
                onChange={(e) => handleChange("activity_level", e.target.value)}
                className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="sedentary">
                  Sedentary (Little/No Exercise)
                </option>
                <option value="lightly_active">
                  Lightly Active (1-3 days/week)
                </option>
                <option value="moderately_active">
                  Moderately Active (3-5 days/week)
                </option>
                <option value="very_active">Very Active (6-7 days/week)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Diet Type
              </label>
              <select
                required
                value={profile.diet_type}
                onChange={(e) => handleChange("diet_type", e.target.value)}
                className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="non_veg">Non-Vegetarian (Any)</option>
                <option value="veg">Vegetarian</option>
                <option value="vegan">Vegan</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Allergies (comma separated)
              </label>
              <input
                type="text"
                placeholder="e.g. peanut, milk, eggs"
                value={allergiesText}
                onChange={(e) => {
                  setAllergiesText(e.target.value);
                  setSaved(false);
                }}
                className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="pt-6">
            <button
              type="submit"
              className="w-full md:w-auto px-8 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all flex items-center justify-center space-x-2"
            >
              {saved ? (
                <>
                  <CheckCircle2 className="w-5 h-5" />{" "}
                  <span>Saved Successfully</span>
                </>
              ) : (
                <span>Save Profile Data</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Profile;
