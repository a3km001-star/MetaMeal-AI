export interface PasswordValidation {
  isValid: boolean;
  checks: {
    minLength: boolean;
    hasUpperCase: boolean;
    hasLowerCase: boolean;
    hasNumbers: boolean;
    hasSpecialChar: boolean;
  };
}

export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email.trim());
};

export const validatePassword = (password: string): PasswordValidation => {
  const minLength = password.length >= 6;
  const hasUpperCase = /[A-Z]/.test(password);
  const hasLowerCase = /[a-z]/.test(password);
  const hasNumbers = /\d/.test(password);
  const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);

  return {
    isValid:
      minLength && hasUpperCase && hasLowerCase && hasNumbers && hasSpecialChar,
    checks: {
      minLength,
      hasUpperCase,
      hasLowerCase,
      hasNumbers,
      hasSpecialChar,
    },
  };
};

export const validateName = (name: string): boolean => {
  return name.trim().length >= 2 && name.trim().length <= 100;
};

export const validateRequired = (value: unknown): boolean => {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "number") return !isNaN(value);
  return true;
};

export const validateNumber = (
  value: string | number,
  min: number | null = null,
  max: number | null = null,
): boolean => {
  const num = typeof value === "string" ? Number(value) : value;
  if (isNaN(num) || !isFinite(num)) return false;
  // For string inputs, verify the string exactly represents the numeric value
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed !== String(num)) return false;
  }
  if (min !== null && num < min) return false;
  if (max !== null && num > max) return false;
  return true;
};

export const validateAge = (age: string | number): boolean => {
  return validateNumber(age, 13, 120);
};

export const validateHeight = (
  height: string | number,
  unit: "cm" | "ft" = "cm",
): boolean => {
  if (unit === "cm") {
    return validateNumber(height, 100, 250);
  }
  return validateNumber(height, 3, 8.5);
};

export const validateWeight = (
  weight: string | number,
  unit: "kg" | "lbs" = "kg",
): boolean => {
  if (unit === "kg") {
    return validateNumber(weight, 30, 300);
  }
  return validateNumber(weight, 66, 660);
};

export const validateCalories = (calories: string | number): boolean => {
  return validateNumber(calories, 0, 10000);
};

export const validateMacros = (grams: string | number): boolean => {
  return validateNumber(grams, 0, 1000);
};

export const validatePercentage = (value: string | number): boolean => {
  return validateNumber(value, 0, 100);
};

export const validateURL = (url: string): boolean => {
  try {
    const urlObj = new URL(url);
    const allowedProtocols = ["http:", "https:"];
    return allowedProtocols.includes(urlObj.protocol.toLowerCase());
  } catch {
    return false;
  }
};

export const validatePhoneNumber = (phone: string): boolean => {
  const phoneRegex =
    /^[+]?[(]?[0-9]{1,4}[)]?[-\s.]?[(]?[0-9]{1,4}[)]?[-\s.]?[0-9]{1,9}$/;
  return phoneRegex.test(phone.trim());
};
