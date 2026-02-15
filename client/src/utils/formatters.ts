export const formatNumber = (num: number | string | null | undefined, decimals = 1): string => {
  if (num === null || num === undefined) return "0";
  const parsed = typeof num === "string" ? parseFloat(num) : num;
  if (isNaN(parsed)) return "0";
  return parsed.toFixed(decimals);
};

export const formatCalories = (calories: number | string): string => {
  const num = typeof calories === "string" ? parseFloat(calories) : calories;
  return `${Math.round(num)} kcal`;
};

export const formatMacros = (grams: number | string, label?: string): string => {
  const num = typeof grams === "string" ? parseFloat(grams) : grams;
  const formatted = Math.round(num);
  return label ? `${formatted}g ${label}` : `${formatted}g`;
};

export const formatProtein = (grams: number | string): string => {
  return formatMacros(grams, "protein");
};

export const formatCarbs = (grams: number | string): string => {
  return formatMacros(grams, "carbs");
};

export const formatFat = (grams: number | string): string => {
  return formatMacros(grams, "fat");
};

export const formatWeight = (
  value: number | string,
  unit: "kg" | "lbs" | "g" = "kg"
): string => {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "0 kg";

  if (unit === "g") {
    if (num < 1000) {
      return `${formatNumber(num, 0)}g`;
    }
    return `${formatNumber(num / 1000, 2)}kg`;
  }

  return `${formatNumber(num, 1)}${unit}`;
};

export const formatHeight = (
  value: number | string,
  unit: "cm" | "ft" = "cm"
): string => {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "0 cm";

  if (unit === "cm") {
    return `${Math.round(num)} cm`;
  }

  const feet = Math.floor(num);
  const inches = Math.round((num - feet) * 12);
  return `${feet}'${inches}"`;
};

export const formatBMI = (bmi: number | string): string => {
  const num = typeof bmi === "string" ? parseFloat(bmi) : bmi;
  if (isNaN(num)) return "0.0";
  return formatNumber(num, 1);
};

export const calculateBMI = (
  weight: number | string,
  height: number | string,
  weightUnit: "kg" | "lbs" = "kg",
  heightUnit: "cm" | "ft" = "cm"
): number => {
  const w = typeof weight === "string" ? parseFloat(weight) : weight;
  const h = typeof height === "string" ? parseFloat(height) : height;

  if (isNaN(w) || isNaN(h) || h === 0) return 0;

  const weightInKg = weightUnit === "lbs" ? w * 0.453592 : w;
  const heightInM = heightUnit === "ft" ? h * 0.3048 : h / 100;

  return weightInKg / (heightInM * heightInM);
};

export const formatPercentage = (
  value: number | string,
  total: number | string,
  decimals = 0
): string => {
  const val = typeof value === "string" ? parseFloat(value) : value;
  const tot = typeof total === "string" ? parseFloat(total) : total;

  if (!tot || tot === 0 || isNaN(val) || isNaN(tot)) return "0%";

  const percentage = (val / tot) * 100;
  return `${formatNumber(percentage, decimals)}%`;
};

export const formatDate = (date: Date | string | number): string => {
  const d = typeof date === "string" || typeof date === "number" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "Invalid Date";

  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

export const formatTime = (date: Date | string | number): string => {
  const d = typeof date === "string" || typeof date === "number" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "Invalid Time";

  return d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const formatDateTime = (date: Date | string | number): string => {
  return `${formatDate(date)} at ${formatTime(date)}`;
};

export const formatDuration = (minutes: number | string): string => {
  const min = typeof minutes === "string" ? parseFloat(minutes) : minutes;
  if (isNaN(min)) return "0 min";

  if (min < 60) {
    return `${Math.round(min)} min`;
  }

  const hours = Math.floor(min / 60);
  const remainingMinutes = Math.round(min % 60);

  if (remainingMinutes === 0) {
    return `${hours} hr`;
  }

  return `${hours} hr ${remainingMinutes} min`;
};

export const formatWorkoutDay = (dayNumber: number): string => {
  const days = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];
  return days[dayNumber - 1] || "Invalid Day";
};

export const formatMealType = (type: string): string => {
  const types: Record<string, string> = {
    breakfast: "Breakfast",
    lunch: "Lunch",
    dinner: "Dinner",
    snack: "Snack",
    snacks: "Snacks",
  };
  return types[type.toLowerCase()] || type;
};

export const formatCurrency = (
  amount: number | string,
  currency = "USD"
): string => {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return "$0.00";

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(num);
};
