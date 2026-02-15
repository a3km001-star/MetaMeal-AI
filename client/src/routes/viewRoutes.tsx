import type { User, ViewType } from "../types";
import DashboardPage from "../pages/DashboardPage";
import MealPlannerPage from "../pages/MealPlannerPage.tsx";
import InsightsPage from "../pages/InsightsPage.tsx";
import CoachPage from "../pages/CoachPage.tsx";
import WorkoutPlannerPage from "../pages/WorkoutPlannerPage.tsx";

export interface ViewRouteContext {
  setActiveView: (view: ViewType) => void;
  user: User;
}

type ViewRouteRenderer = (context: ViewRouteContext) => JSX.Element;

const viewRoutes: Record<ViewType, ViewRouteRenderer> = {
  dashboard: ({ setActiveView, user }) => (
    <DashboardPage setActiveView={setActiveView} user={user} />
  ),
  "meal-planner": () => <MealPlannerPage />,
  insights: () => <InsightsPage />,
  coach: ({ setActiveView }) => <CoachPage setActiveView={setActiveView} />,
  "workout-planner": () => <WorkoutPlannerPage />,
};

export const renderActiveView = (
  activeView: ViewType,
  context: ViewRouteContext,
): JSX.Element => viewRoutes[activeView](context);
