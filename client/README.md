# MetaMeal AI - Nutrition Platform

A high-fidelity, responsive Single Page Application (SPA) prototype for a nutrition platform built with React, Tailwind CSS, and Lucide-React icons.

## Features

### Authentication

- Modern login/register interface with toggle functionality
- Email and password fields
- Auto-login to dashboard after sign in

### Dashboard

- Personalized greeting for user
- Streak tracking card with gradient design
- Three interactive action cards:
  - Generate Meal Plan
  - Analyze Food (coming soon)
  - Ask Coach
- Quick stats display

### Meal Planner

- Horizontal scrollable calendar with date selection
- Macro nutrient tracking (Calories, Protein, Carbs, Fat)
- Detailed meal cards for Breakfast, Lunch, Dinner, and Snacks
- "Create New Plan" button with loading animation

### Insights

- Skeleton placeholder charts for:
  - Weight Trend
  - Protein Intake
  - Calorie Consistency
- Weekly summary statistics

### AI Coach

- Chat-style interface
- Scrollable message area
- Quick question shortcuts
- Real-time message simulation

### Navigation

- Fixed top navbar with MetaMeal AI logo
- User name display and logout functionality
- Responsive footer with 4 columns (Product, Company, Support, Social)

## Tech Stack

- **React 18.3** - UI framework
- **Vite 6.0** - Build tool
- **Tailwind CSS 3.4** - Styling
- **Lucide React** - Icon library

## Getting Started

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Design Features

- **Color Palette**: Gray-50 background, white cards, pastel accent colors
- **Responsive**: Mobile-first design with breakpoints for tablets and desktops
- **Interactive**: Hover states with scale and shadow effects
- **Animations**: Smooth transitions and loading states
- **Typography**: Clean, modern font hierarchy

## Default Login

> **SECURITY WARNING**
> This is a demo/prototype-only authentication stub. Do not use in production.
> Maintainers must disable or remove this stub before deployment and implement
> proper authentication (real credential checks, session management, and
> env-based flags to gate demo mode).

- Email: Any valid email format
- Password: Any password
- User: Automatically logged in as "Ayan"

## Project Structure

```
src/
├── components/
│   ├── Auth.jsx          # Login/Register view
│   ├── Navbar.jsx        # Top navigation
│   ├── Footer.jsx        # Bottom footer
│   ├── Dashboard.jsx     # Main dashboard
│   ├── MealPlanner.jsx   # Meal planning view
│   ├── Insights.jsx      # Analytics view
│   └── Coach.jsx         # AI coach chat
├── App.jsx               # Main app component
├── main.jsx              # Entry point
└── index.css             # Global styles
```

## License

MIT
