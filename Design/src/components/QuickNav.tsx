import { Utensils, Scan, MessageCircle, Dumbbell } from "lucide-react";

type ViewType =
  | "dashboard"
  | "meal-planner"
  | "insights"
  | "coach"
  | "workout-planner";

interface NavItem {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  hoverColor: string;
}

interface QuickNavProps {
  setActiveView: (view: ViewType) => void;
}

function QuickNav({ setActiveView }: QuickNavProps) {
  const navItems: NavItem[] = [
    {
      id: "meal-planner",
      name: "Generate Meals",
      icon: Utensils,
      color: "from-green-500 to-emerald-600",
      hoverColor: "hover:from-green-600 hover:to-emerald-700",
    },
    {
      id: "analyze-food",
      name: "Analyze Food",
      icon: Scan,
      color: "from-purple-500 to-pink-600",
      hoverColor: "hover:from-purple-600 hover:to-pink-700",
    },
    {
      id: "coach",
      name: "Ask Coach",
      icon: MessageCircle,
      color: "from-blue-500 to-cyan-600",
      hoverColor: "hover:from-blue-600 hover:to-cyan-700",
    },
    {
      id: "workout-planner",
      name: "Workout Plan",
      icon: Dumbbell,
      color: "from-orange-500 to-red-600",
      hoverColor: "hover:from-orange-600 hover:to-red-700",
    },
  ];

  const handleNavClick = (id: string): void => {
    if (id === "analyze-food") {
      alert("Feature Coming Soon!");
    } else {
      setActiveView(id as ViewType);
    }
  };

  return (
    <div className="mb-8">
      <div className="bg-white rounded-2xl p-6 shadow-md">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Quick Access
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id)}
              className={`flex flex-col items-center justify-center p-4 rounded-xl bg-gradient-to-br ${item.color} ${item.hoverColor} text-white shadow-md hover:shadow-lg hover:scale-105 transition-all`}
            >
              <item.icon className="w-8 h-8 mb-2" />
              <span className="text-sm font-semibold text-center">
                {item.name}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default QuickNav;
