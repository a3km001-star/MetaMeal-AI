import MealPlanner from "../components/MealPlanner";
import type { ViewType } from "../types";

interface MealPlannerPageProps {
  setActiveView: (view: ViewType) => void;
}

function MealPlannerPage({ setActiveView }: MealPlannerPageProps) {
  return <MealPlanner setActiveView={setActiveView} />;
}

export default MealPlannerPage;
