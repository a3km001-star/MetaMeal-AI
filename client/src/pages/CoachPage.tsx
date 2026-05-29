import Coach from "../components/Coach";
import type { User, ViewType } from "../types";

interface CoachPageProps {
  setActiveView: (view: ViewType) => void;
  user: User;
}

function CoachPage({ setActiveView, user }: CoachPageProps) {
  return <Coach setActiveView={setActiveView} user={user} />;
}

export default CoachPage;
