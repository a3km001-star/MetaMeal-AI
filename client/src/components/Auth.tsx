import { useState, useActionState, use } from "react";
import axios from "axios";
import { Autocomplete, Chip, TextField } from "@mui/material";
import {
  Mail,
  Lock,
  User,
  Scale,
  Ruler,
  Calendar,
  Moon,
  Sun,
} from "lucide-react";

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

type AuthMode = "login" | "register";

interface AuthProps {
  onLogin: (name: string) => void;
  initialMode?: AuthMode;
  darkMode: boolean;
  toggleDarkMode: () => void;
}

interface RegisterFormState {
  error: string | null;
  success: boolean;
}

interface InputFieldProps {
  label: string;
  icon: React.ReactNode;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  required?: boolean;
  min?: number;
  max?: number;
  step?: number;
  minLength?: number;
}

function InputField({
  label,
  icon,
  type = "text",
  value,
  onChange,
  placeholder,
  required,
  min,
  max,
  step,
  minLength,
}: InputFieldProps) {
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
          className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
          placeholder={placeholder}
          required={required}
          min={min}
          max={max}
          step={step}
          minLength={minLength}
        />
      </div>
    </div>
  );
}

interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  children: React.ReactNode;
}

function SelectField({
  label,
  value,
  onChange,
  required,
  children,
}: SelectFieldProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
        required={required}
      >
        {children}
      </select>
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

  // shared fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // register-only fields
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [gender, setGender] = useState("");
  const [workoutExperience, setWorkoutExperience] = useState("");
  const [dietPreference, setDietPreference] = useState("");
  const [goal, setGoal] = useState("");
  const [activityLevel, setActivityLevel] = useState("");
  const [allergies, setAllergies] = useState<string[]>([]);
  const [confirmPassword, setConfirmPassword] = useState("");

  // useActionState replaces manual loading/error state management
  const [registerState, registerAction, isRegisterPending] = useActionState<
    RegisterFormState,
    FormData
  >(
    async (_prevState, _formData) => {
      if (password !== confirmPassword) {
        return { error: "Passwords do not match!", success: false };
      }
      try {
        await axios.post("http://localhost:3001/register", {
          name,
          email,
          password,
          age,
          height,
          weight,
          gender,
          workoutExperience,
          dietPreference,
          goal,
          activityLevel,
          allergies,
        });
        onLogin(name);
        return { error: null, success: true };
      } catch {
        return {
          error: "Registration failed. Please try again.",
          success: false,
        };
      }
    },
    { error: null, success: false },
  );

  function handleSignIn(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    onLogin(email.split("@")[0] || "User");
  }

  const allergyAutocompleteStyles = {
    "& .MuiOutlinedInput-root": {
      color: darkMode ? "#fff" : "#000",
      bgcolor: darkMode ? "#374151" : "#fff",
      "& fieldset": {
        borderColor: darkMode ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.23)",
      },
      "&:hover fieldset": {
        borderColor: darkMode ? "rgba(255,255,255,0.4)" : "rgba(0,0,0,0.4)",
      },
      "&.Mui-focused fieldset": {
        borderColor: darkMode ? "#60A5FA" : "#3b82f6",
      },
    },
    "& .MuiInputLabel-root": {
      color: darkMode ? "rgba(255,255,255,0.7)" : "rgba(0,0,0,0.7)",
    },
  };

  const dropdownSx = {
    bgcolor: darkMode ? "#1f2937" : "#fff",
    color: darkMode ? "#fff" : "#000",
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4 transition-colors duration-300">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md p-8 relative transition-colors duration-300">
        <button
          onClick={toggleDarkMode}
          className="absolute top-4 right-4 p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-all"
          aria-label="Toggle dark mode"
        >
          {darkMode ? (
            <Sun className="w-5 h-5 text-yellow-500" />
          ) : (
            <Moon className="w-5 h-5 text-gray-700" />
          )}
        </button>

        <div className="flex justify-center mb-6">
          <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full p-4">
            <User className="w-8 h-8 text-white" />
          </div>
        </div>

        <h1 className="text-3xl font-bold text-center text-gray-800 dark:text-white mb-2">
          Welcome to MetaMeal
        </h1>
        <p className="text-center text-gray-600 dark:text-gray-400 mb-8">
          Your personal nutrition companion
        </p>

        <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1 mb-6">
          <button
            onClick={() => setIsSignIn(true)}
            className={`flex-1 py-2 px-4 rounded-md font-medium transition-all ${
              isSignIn
                ? "bg-white dark:bg-gray-600 text-blue-600 dark:text-white shadow-sm"
                : "text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white"
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => setIsSignIn(false)}
            className={`flex-1 py-2 px-4 rounded-md font-medium transition-all ${
              !isSignIn
                ? "bg-white dark:bg-gray-600 text-blue-600 dark:text-white shadow-sm"
                : "text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white"
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Error message from register action */}
        {registerState.error && (
          <p className="text-red-500 text-sm text-center mb-4">
            {registerState.error}
          </p>
        )}

        {isSignIn ? (
          <form onSubmit={handleSignIn} className="space-y-4">
            <InputField
              label="Email"
              icon={<Mail className="w-5 h-5" />}
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="Enter your email"
              required
            />
            <InputField
              label="Password"
              icon={<Lock className="w-5 h-5" />}
              type="password"
              value={password}
              onChange={setPassword}
              placeholder="Enter your password"
              required
              minLength={6}
            />
            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2">
                <input type="checkbox" />
                <span className="text-gray-600 dark:text-gray-300">
                  Remember me
                </span>
              </label>
              <a
                href="#"
                className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
              >
                Forgot password?
              </a>
            </div>
            <button
              type="submit"
              className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 rounded-lg font-semibold hover:shadow-lg hover:scale-105 transition-all"
            >
              Sign In
            </button>
          </form>
        ) : (
          // React 19 form action wired to useActionState
          <form
            action={registerAction}
            className="space-y-4 max-h-[60vh] overflow-y-auto px-2"
          >
            <InputField
              label="Full Name"
              icon={<User className="w-5 h-5" />}
              value={name}
              onChange={setName}
              placeholder="Enter your full name"
              required
            />

            <div className="grid grid-cols-2 gap-4">
              <InputField
                label="Age"
                icon={<Calendar className="w-5 h-5" />}
                type="number"
                value={age}
                onChange={setAge}
                placeholder="Age"
                required
                min={13}
                max={120}
              />
              <InputField
                label="Height (cm)"
                icon={<Ruler className="w-5 h-5" />}
                type="number"
                value={height}
                onChange={setHeight}
                placeholder="Height"
                required
                min={100}
                max={250}
              />
            </div>

            <SelectField
              label="Gender"
              value={gender}
              onChange={setGender}
              required
            >
              <option value="">Select gender</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </SelectField>

            <InputField
              label="Weight (kg)"
              icon={<Scale className="w-5 h-5" />}
              type="number"
              value={weight}
              onChange={setWeight}
              placeholder="Enter your weight"
              required
              min={30}
              max={300}
              step={0.1}
            />

            <SelectField
              label="Workout Experience Level"
              value={workoutExperience}
              onChange={setWorkoutExperience}
              required
            >
              <option value="">Select experience level</option>
              <option value="beginner">Beginner (0-6 months)</option>
              <option value="intermediate">
                Intermediate (6 months - 2 years)
              </option>
              <option value="advanced">Advanced (2+ years)</option>
            </SelectField>

            <SelectField
              label="Diet Preference"
              value={dietPreference}
              onChange={setDietPreference}
              required
            >
              <option value="">Select diet preference</option>
              <option value="balanced">Balanced</option>
              <option value="vegetarian">Vegetarian</option>
              <option value="vegan">Vegan</option>
              <option value="keto">Keto</option>
              <option value="paleo">Paleo</option>
              <option value="low-carb">Low Carb</option>
            </SelectField>

            <Autocomplete
              multiple
              options={allergyOptions}
              value={allergies}
              onChange={(_event, newValue) => setAllergies(newValue)}
              disableCloseOnSelect
              filterSelectedOptions
              getOptionLabel={(option) => option}
              slotProps={{
                paper: { sx: dropdownSx },
                listbox: { sx: dropdownSx },
              }}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip
                    variant="outlined"
                    label={option}
                    {...getTagProps({ index })}
                    key={option}
                    sx={{
                      color: darkMode ? "#fff" : "inherit",
                      bgcolor: darkMode ? "rgba(255,255,255,0.12)" : "inherit",
                      borderColor: darkMode
                        ? "rgba(255,255,255,0.3)"
                        : "inherit",
                    }}
                  />
                ))
              }
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Allergies (optional)"
                  placeholder="Start typing to search"
                  variant="outlined"
                  size="small"
                  sx={allergyAutocompleteStyles}
                />
              )}
            />

            <SelectField
              label="Fitness Goal"
              value={goal}
              onChange={setGoal}
              required
            >
              <option value="">Select your goal</option>
              <option value="weight-loss">Weight Loss</option>
              <option value="weight-gain">Weight Gain</option>
              <option value="maintain">Maintain Weight</option>
              <option value="muscle-gain">Muscle Gain</option>
            </SelectField>

            <SelectField
              label="Activity Level"
              value={activityLevel}
              onChange={setActivityLevel}
              required
            >
              <option value="">Select activity level</option>
              <option value="sedentary">
                Sedentary (Little to no exercise)
              </option>
              <option value="light">Lightly Active (1-3 days/week)</option>
              <option value="moderate">
                Moderately Active (3-5 days/week)
              </option>
              <option value="very-active">Very Active (6-7 days/week)</option>
              <option value="extra-active">
                Extra Active (Physical job + exercise)
              </option>
            </SelectField>

            <InputField
              label="Email"
              icon={<Mail className="w-5 h-5" />}
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="Enter your email"
              required
            />

            <InputField
              label="Password"
              icon={<Lock className="w-5 h-5" />}
              type="password"
              value={password}
              onChange={setPassword}
              placeholder="Enter your password"
              required
              minLength={6}
            />

            <InputField
              label="Confirm Password"
              icon={<Lock className="w-5 h-5" />}
              type="password"
              value={confirmPassword}
              onChange={setConfirmPassword}
              placeholder="Confirm your password"
              required
              minLength={6}
            />

            <button
              type="submit"
              disabled={isRegisterPending}
              className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 rounded-lg font-semibold hover:shadow-lg hover:scale-105 transition-all disabled:opacity-60 disabled:cursor-not-allowed disabled:scale-100"
            >
              {isRegisterPending ? "Creating Account..." : "Create Account"}
            </button>
          </form>
        )}

        <p className="text-center text-gray-600 dark:text-gray-400 text-sm mt-6">
          {isSignIn ? "Don't have an account? " : "Already have an account? "}
          <button
            onClick={() => setIsSignIn(!isSignIn)}
            className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
          >
            {isSignIn ? "Create one" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}

export default Auth;
