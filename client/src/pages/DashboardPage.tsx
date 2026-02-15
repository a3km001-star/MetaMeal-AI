import Dashboard from "../components/Dashboard";
import type { User, ViewType } from "../types";

interface DashboardPageProps {
  setActiveView: (view: ViewType) => void;
  user: User;
}

function DashboardPage({ setActiveView, user }: DashboardPageProps) {
  return <Dashboard setActiveView={setActiveView} user={user} />;
}

export default DashboardPage;
