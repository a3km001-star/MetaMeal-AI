// Validation Constants
export const VALIDATION_LIMITS = {
  AGE: {
    MIN: 13,
    MAX: 120,
  },
  HEIGHT: {
    CM: {
      MIN: 100,
      MAX: 250,
    },
    FT: {
      MIN: 3,
      MAX: 8.5,
    },
  },
  WEIGHT: {
    KG: {
      MIN: 30,
      MAX: 300,
    },
    LBS: {
      MIN: 66,
      MAX: 660,
    },
  },
  PASSWORD: {
    MIN_LENGTH: 6,
  },
  NAME: {
    MIN_LENGTH: 2,
    MAX_LENGTH: 100,
  },
  CALORIES: {
    MIN: 0,
    MAX: 10000,
  },
  MACROS: {
    MIN: 0,
    MAX: 1000,
  },
} as const;

// Workout Experience Levels
export const WORKOUT_EXPERIENCE = {
  BEGINNER: "beginner",
  INTERMEDIATE: "intermediate",
  ADVANCED: "advanced",
} as const;

// Diet Preferences
export const DIET_PREFERENCES = {
  BALANCED: "balanced",
  VEGETARIAN: "vegetarian",
  VEGAN: "vegan",
  KETO: "keto",
  PALEO: "paleo",
  LOW_CARB: "low-carb",
} as const;

// Fitness Goals
export const FITNESS_GOALS = {
  WEIGHT_LOSS: "weight-loss",
  WEIGHT_GAIN: "weight-gain",
  MAINTAIN: "maintain",
  MUSCLE_GAIN: "muscle-gain",
} as const;

// Activity Levels
export const ACTIVITY_LEVELS = {
  SEDENTARY: "sedentary",
  LIGHT: "light",
  MODERATE: "moderate",
  VERY_ACTIVE: "very-active",
  EXTRA_ACTIVE: "extra-active",
} as const;

// Meal Types
export const MEAL_TYPES = {
  BREAKFAST: "breakfast",
  LUNCH: "lunch",
  DINNER: "dinner",
  SNACK: "snack",
  SNACKS: "snacks",
} as const;

// Days of the Week
export const DAYS_OF_WEEK = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;

// BMI Categories
export const BMI_CATEGORIES = {
  UNDERWEIGHT: { max: 18.5, label: "Underweight" },
  NORMAL: { min: 18.5, max: 24.9, label: "Normal" },
  OVERWEIGHT: { min: 25, max: 29.9, label: "Overweight" },
  OBESE: { min: 30, label: "Obese" },
} as const;

// Unit Conversions
export const CONVERSIONS = {
  KG_TO_LBS: 2.20462,
  LBS_TO_KG: 0.453592,
  CM_TO_FT: 0.0328084,
  FT_TO_CM: 30.48,
  CM_TO_M: 0.01,
} as const;
