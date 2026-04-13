"""Tests for deterministic cross-module sync checks."""

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_sync_check_happy_path():
    payload = {
        "user_profile": {
            "goal": "muscle_gain",
            "weight": 75,
            "activity_level": "moderately_active",
        },
        "meal_plan_output": {
            "calorie_target": 2600,
            "macros": {
                "protein": 150,
                "carbs": 300,
                "fat": 70,
            },
        },
        "workout_plan_output": {
            "weekly_plan": {
                "day_1": {"type": "push", "exercises": [{"exercise": "A", "muscle": "chest", "sets": 4, "reps": "8-12", "rest": "120 sec"}]},
                "day_2": {"type": "pull", "exercises": [{"exercise": "B", "muscle": "back", "sets": 4, "reps": "8-12", "rest": "120 sec"}]},
                "day_3": {"type": "legs", "exercises": [{"exercise": "C", "muscle": "quads", "sets": 4, "reps": "8-12", "rest": "120 sec"}]},
                "day_4": {"type": "upper", "exercises": [{"exercise": "D", "muscle": "shoulders", "sets": 4, "reps": "8-12", "rest": "60 sec"}]},
                "day_5": {"type": "lower", "exercises": [{"exercise": "E", "muscle": "hamstrings", "sets": 4, "reps": "8-12", "rest": "60 sec"}]},
                "day_6": {"type": "rest", "exercises": []},
                "day_7": {"type": "rest", "exercises": []},
            }
        },
    }

    response = client.post("/sync/check", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["synchronized"] is True
    assert body["score"] == 100


def test_sync_check_detects_low_calorie_high_load_conflict():
    weekly_plan = {}
    for i in range(1, 8):
        weekly_plan[f"day_{i}"] = {
            "type": "push" if i <= 6 else "rest",
            "exercises": [
                {"exercise": f"X{i}", "muscle": "chest", "sets": 15 if i <= 5 else 0, "reps": "8-12", "rest": "120 sec"}
            ] if i <= 6 else [],
        }

    payload = {
        "user_profile": {"goal": "muscle_gain", "weight": 75},
        "meal_plan_output": {"calorie_target": 1500, "macros": {"protein": 90, "carbs": 130, "fat": 40}},
        "workout_plan_output": {"weekly_plan": weekly_plan},
    }

    response = client.post("/sync/check", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["synchronized"] is False
    assert len(body["mismatches"]) >= 1
