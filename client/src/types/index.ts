import type { ComponentType } from "react";

export interface UserProfileData {
  age?: number;
  height?: number;
  weight?: number;
  sex?: string;
  diet_type?: string;
  activity_level?: string;
  goal?: string;
  allergies?: string[];
}

export interface User extends UserProfileData {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export type ViewType =
  | "dashboard"
  | "meal-planner"
  | "insights"
  | "coach"
  | "workout-planner"
  | "profile"; // Added profile view

export type AuthMode = "login" | "register";

export interface NavItem {
  id: ViewType;
  name: string;
  icon: ComponentType<{ className?: string }>;
}

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
  user_details?: Record<string, any> | null;
  first_meal_generation?: Record<string, any> | null;
  last_meal_generation_date?: string | null;
  meal_generation_streak: number;
}
