import type { ComponentType } from "react";

export interface User {
  name: string;
}

export type ViewType =
  | "dashboard"
  | "meal-planner"
  | "insights"
  | "coach"
  | "workout-planner";

export type AuthMode = "login" | "register";

export interface NavItem {
  id: ViewType;
  name: string;
  icon: ComponentType<{ className?: string }>;
}
