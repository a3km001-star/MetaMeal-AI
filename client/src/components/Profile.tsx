import { useState, useEffect } from "react";
import { User, Scale, Ruler, Calendar, CheckCircle2, X } from "lucide-react";
import { getMe } from "../api/auth";
import type { UserProfileData } from "../types";

const allergyOptions = [
  "Amaranth",
  "Bajra",
  "Barley",
  "Jowar",
  "Maize",
  "Quinoa",
  "Ragi",
  "Rice",
  "Samai",
  "Varagu",
  "Wheat",
  "Bengal gram",
  "Black gram",
  "Cowpea",
  "Field bean",
  "Green gram",
  "Horse gram",
  "Lentil",
  "Moth bean",
  "Peas",
  "Rajmah",
  "Red gram",
  "Ricebean",
  "Soya bean",
  "Agathi leaves",
  "Amaranth leaves",
  "Basella leaves",
  "Bathua leaves",
  "Beet greens",
  "Betel leaves",
  "Brussels sprouts",
  "Cabbage",
  "Cauliflower leaves",
  "Colocasia leaves",
  "Drumstick leaves",
  "Fenugreek leaves",
  "Garden cress",
  "Gogu leaves",
  "Knol-Khol leaves",
  "Lettuce",
  "Mustard leaves",
  "Pak Choi leaves",
  "Parsley",
  "Ponnaganni",
  "Pumpkin leaves",
  "Radish leaves",
  "Rumex leaves",
  "Spinach",
  "Tamarind leaves",
  "Ash gourd",
  "Bamboo shoot",
  "Bean scarlet",
  "Bitter gourd",
  "Bottle gourd",
  "Brinjal",
  "Broad beans",
  "Capsicum",
  "Cauliflower",
  "Celery",
  "Cho-cho-marrow",
  "Cluster beans",
  "Colocasia stem",
  "Corn",
  "Cucumber",
  "Drumstick",
  "Field beans",
  "French beans",
  "Jack fruit",
  "Knol-Khol",
  "Kovai",
  "Ladies finger",
  "Mango",
  "Onion stalk",
  "Papaya",
  "Parwar",
  "Plantain",
  "Pumpkin",
  "Ridge gourd",
  "Snake gourd",
  "Tinda",
  "Tomato",
  "Zucchini",
  "Apple",
  "Apricot",
  "Avocado",
  "Bael",
  "Banana",
  "Blackberry",
  "Cherries",
  "Currants",
  "Custard apple",
  "Dates",
  "Fig",
  "Gooseberry",
  "Grapes",
  "Guava",
  "Jambu fruit",
  "Karonda",
  "Lemon",
  "Lime",
  "Litchi",
  "Mangosteen",
  "Manila tamarind",
  "Musk melon",
  "Orange",
  "Palm fruit",
  "Peach",
  "Pear",
  "Phalsa",
  "Pineapple",
  "Plum",
  "Pomegranate",
  "Pummelo",
  "Raisins",
  "Rambutan",
  "Sapota",
  "Soursop",
  "Star fruit",
  "Strawberry",
  "Tamarind",
  "Watermelon",
  "Wood apple",
  "Zizyphus",
  "Beetroot",
  "Carrot",
  "Colocasia",
  "Lotus root",
  "Potato",
  "Radish",
  "Sweet potato",
  "Tapioca",
  "Water chestnut",
  "Yam",
  "Chillies",
  "Coriander leaves",
  "Curry leaves",
  "Garlic",
  "Ginger",
  "Mango ginger",
  "Mint leaves",
  "Onion",
  "Asafoetida",
  "Cardamom",
  "Cloves",
  "Coriander seeds",
  "Cumin seeds",
  "Fenugreek seeds",
  "Mace",
  "Nutmeg",
  "Omum",
  "Pippali",
  "Pepper",
  "Poppy seeds",
  "Turmeric",
  "Almond",
  "Arecanut",
  "Cashew nut",
  "Coconut",
  "Gingelly seeds",
  "Groundnut",
  "Mustard seeds",
  "Linseeds",
  "Niger seeds",
  "Pine seed",
  "Pistachio",
  "Safflower seeds",
  "Sunflower seeds",
  "Walnut",
  "Jaggery",
  "Sugarcane",
  "Mushroom",
  "Toddy",
  "Coconut water",
  "Milk",
  "Paneer",
  "Khoa",
  "Egg",
  "eggs",
  "Chicken",
  "Country hen",
  "Duck",
  "Quail",
  "Turkey",
  "Goat",
  "Sheep",
  "Beef",
  "Calf",
  "Mithun",
  "Pork",
  "Hare",
  "Rabbit",
  "Fish",
  "Anchovy",
  "Betki",
  "Black snapper",
  "Bombay duck",
  "Cat fish",
  "Hilsa",
  "Mackerel",
  "Milk fish",
  "Mullet",
  "Pomfret",
  "Red snapper",
  "Salmon",
  "Sardine",
  "Shark",
  "Silver carp",
  "Sole fish",
  "Stingray",
  "Tilapia",
  "Tuna",
  "Vanjaram",
  "Crab",
  "Lobster",
  "Mud crab",
  "Oyster",
  "Prawns",
  "Clam",
  "Octopus",
  "Squid",
  "Catla",
  "Freshwater eel",
  "Gold fish",
  "Pangas",
  "Rohu",
  "Coconut oil",
  "Corn oil",
  "Cotton seed oil",
  "Gingelly oil",
  "Groundnut oil",
  "Mustard oil",
  "Palm oil",
  "Rice bran oil",
  "Safflower oil",
  "Soyabean oil",
  "Sunflower oil",
  "Ghee",
  "Vanaspati",
];

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
  const [allergies, setAllergies] = useState<string[]>([]);

  useEffect(() => {
    const fetchProfileData = async () => {
      try {
        // 1. Try to get the latest profile from the database
        const res = await getMe();
        if (res.data.user_details) {
          setProfile(res.data.user_details);
          const serverAllergies = Array.isArray(res.data.user_details.allergies)
            ? res.data.user_details.allergies
            : [];
          setAllergies(serverAllergies);
          setAllergiesText("");
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
        setAllergies(Array.isArray(parsed.allergies) ? parsed.allergies : []);
        setAllergiesText("");
      }
    };

    fetchProfileData();

    // Listen for profile updates from other components (Insights)
    const handler = async (e: any) => {
      try {
        // If detailed info exists, prefer a fresh fetch from server
        await fetchProfileData();
      } catch (err) {
        console.error("Failed to refresh profile after update:", err);
      }
    };

    window.addEventListener("profileUpdated", handler as EventListener);
    return () => {
      window.removeEventListener("profileUpdated", handler as EventListener);
    };
  }, []);

  const handleChange = (field: keyof UserProfileData, value: any) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const updatedProfile = {
      ...profile,
      allergies,
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

  const addAllergy = (allergy: string) => {
    const normalized = allergy.trim().toLowerCase();
    if (!normalized || allergies.includes(normalized)) return;
    setAllergies((prev) => [...prev, normalized]);
    setAllergiesText("");
    setSaved(false);
  };

  const removeAllergy = (allergy: string) => {
    setAllergies((prev) => prev.filter((item) => item !== allergy));
    setSaved(false);
  };

  const filteredSuggestions = allergyOptions.filter((option) => {
    const normalizedOption = option.toLowerCase();
    const normalizedInput = allergiesText.trim().toLowerCase();
    return (
      normalizedInput.length > 0 &&
      normalizedOption.includes(normalizedInput) &&
      !allergies.includes(normalizedOption)
    );
  });

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
                Allergies
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {allergies.map((allergy) => (
                  <span
                    key={allergy}
                    className="inline-flex items-center gap-2 rounded-full bg-red-100 dark:bg-red-900/40 px-3 py-1 text-sm text-red-700 dark:text-red-200"
                  >
                    {allergy}
                    <button
                      type="button"
                      onClick={() => removeAllergy(allergy)}
                      className="rounded-full p-0.5 hover:bg-red-200 dark:hover:bg-red-800"
                      aria-label={`Remove ${allergy}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Type allergy to see suggestions"
                  value={allergiesText}
                  onChange={(e) => {
                    setAllergiesText(e.target.value);
                    setSaved(false);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      if (allergiesText.trim().length > 0) {
                        addAllergy(allergiesText);
                      }
                    }
                  }}
                  className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
                />
                {filteredSuggestions.length > 0 && (
                  <div className="absolute left-0 right-0 mt-1 z-10 rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800 shadow-lg max-h-44 overflow-y-auto">
                    {filteredSuggestions.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        onClick={() => addAllergy(suggestion)}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
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
