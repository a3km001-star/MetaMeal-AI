import React from "react";
import type { User, ViewType } from "../types";
import DashboardPage from "../pages/DashboardPage";
import MealPlannerPage from "../pages/MealPlannerPage";
import InsightsPage from "../pages/InsightsPage";
import CoachPage from "../pages/CoachPage";
import WorkoutPlannerPage from "../pages/WorkoutPlannerPage";
import Profile from "../components/Profile";

export interface ViewRouteContext {
  setActiveView: (view: ViewType) => void;
  user: User;
}

type ViewRouteRenderer = (context: ViewRouteContext) => React.JSX.Element;

const viewRoutes: Record<ViewType, ViewRouteRenderer> = {
  dashboard: ({ setActiveView, user }) => (
    <DashboardPage setActiveView={setActiveView} user={user} />
  ),
  "meal-planner": ({ setActiveView }) => (
    <MealPlannerPage setActiveView={setActiveView} />
  ),
  insights: () => <InsightsPage />,
  coach: ({ setActiveView }) => <CoachPage setActiveView={setActiveView} />,
  "workout-planner": () => <WorkoutPlannerPage />,
  profile: () => <Profile />,
};

export const renderActiveView = (
  activeView: ViewType,
  context: ViewRouteContext,
): React.JSX.Element => viewRoutes[activeView](context);
