# MetaMeal-AI

Hybrid AI Nutrition & Fitness system with a React SPA frontend and a FastAPI backend.

## Architecture Overview

- **Frontend**: React + Vite + Tailwind (client/)
- **Backend**: FastAPI + MongoDB + Groq LLM (server/)
- **Core flows**:
  - Auth → meal/workout generation → progress logging → AI coach/chatbot

## Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB connection string
- Groq API key (for workout LLM + chatbot)

## Local Setup

### 1) Backend

```bash
cd server
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create `server/.env`:

```ini
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>/<db>
GROQ_API_KEY=<your_groq_key>
JWT_SECRET=<your_secret>
```

Run the API:

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

### 2) Frontend

```bash
cd client
npm install
npm run dev
```

Optional: point the client at your local API in `client/.env`:

```ini
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## API Quick Start (local)

1. Register/login
2. Generate meal/workout
3. Chat with the AI coach

See backend details and curl examples in [server/Readme.md](server/Readme.md).

## Project Structure

```
client/   # React app
server/   # FastAPI backend
Dataset/  # Nutrition data and scripts
```

## Team - a3km

1. Manish Bera (Impact Player for Opponents)
2. Kritika Das (C) (Opener 1)
3. Khusboo Agarwalla (Opener 2)
4. Koushik Adhikary (Owner)
5. Ayan Guchhait (45)
