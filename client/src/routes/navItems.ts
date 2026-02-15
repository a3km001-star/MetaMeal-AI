import {
  LayoutDashboard,
  Utensils,
  TrendingUp,
  MessageCircle,
  Dumbbell,
} from "lucide-react";
import type { NavItem } from "../types";

export const navItems: NavItem[] = [
  { id: "dashboard", name: "Dashboard", icon: LayoutDashboard },
  { id: "meal-planner", name: "Meals", icon: Utensils },
  { id: "workout-planner", name: "Workout", icon: Dumbbell },
  { id: "insights", name: "Insights", icon: TrendingUp },
  { id: "coach", name: "Coach", icon: MessageCircle },
];
