import Coach from "../components/Coach";
import type { ViewType } from "../types";

interface CoachPageProps {
  setActiveView: (view: ViewType) => void;
}

function CoachPage({ setActiveView }: CoachPageProps) {
  return <Coach setActiveView={setActiveView} />;
}

export default CoachPage;
