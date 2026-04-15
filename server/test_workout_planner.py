"""End-to-end tests for workout planner API and engine constraints."""

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def _sum_sets_by_muscle(weekly_plan):
    totals = {}
    for day in weekly_plan.values():
        for ex in day.get("exercises", []):
            muscle = ex["muscle"]
            totals[muscle] = totals.get(muscle, 0) + int(ex["sets"])
    return totals


def test_workout_generate_push_pull_legs_5day_end_to_end():
    payload = {
        "goal": "muscle_gain",
        "experience_level": "intermediate",
        "split": "push_pull_legs",
        "training_days": 5,
        "weekly_volume_per_muscle": 12,
        "equipment": "gym",
        "injuries": [],
        "focus_muscles": ["chest", "back"],
    }

    response = client.post("/workout/generate", json=payload)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["success"] is True
    weekly_plan = body["data"]["weekly_plan"]

    assert len(weekly_plan) == 7

    day_types = [weekly_plan[f"day_{i}"]["type"] for i in range(1, 8)]
    assert day_types == ["push", "pull", "legs", "push", "pull", "rest", "rest"]

    for i in range(1, 6):
        exercises = weekly_plan[f"day_{i}"]["exercises"]
        assert len(exercises) == 5

    assert weekly_plan["day_6"]["exercises"] == []
    assert weekly_plan["day_7"]["exercises"] == []

    totals = _sum_sets_by_muscle(weekly_plan)
    expected_muscles = {
        "chest",
        "shoulders",
        "triceps",
        "back",
        "biceps",
        "rear_delts",
        "quads",
        "hamstrings",
        "glutes",
        "calves",
    }
    assert set(totals.keys()) == expected_muscles
    for muscle in expected_muscles:
        assert totals[muscle] == 12


def test_workout_respects_injury_filter():
    payload = {
        "goal": "fat_loss",
        "experience_level": "beginner",
        "split": "upper_lower",
        "training_days": 4,
        "weekly_volume_per_muscle": {
            "chest": 8,
            "back": 8,
            "shoulders": 8,
            "biceps": 8,
            "triceps": 8,
            "quads": 8,
            "hamstrings": 8,
            "glutes": 8,
            "calves": 8,
        },
        "equipment": "gym",
        "injuries": ["shoulder"],
        "focus_muscles": [],
    }

    response = client.post("/workout/generate", json=payload)
    assert response.status_code == 200, response.text

    weekly_plan = response.json()["data"]["weekly_plan"]
    forbidden_keywords = ["Press", "Lateral Raise", "Face Pull", "Reverse Pec Deck", "Pull-Up"]

    for day in weekly_plan.values():
        for ex in day.get("exercises", []):
            assert not any(key.lower() in ex["exercise"].lower() for key in forbidden_keywords)


def test_workout_accepts_maintenance_goal():
    payload = {
        "goal": "maintenance",
        "experience_level": "beginner",
        "split": "push_pull_legs",
        "training_days": 3,
        "weekly_volume_per_muscle": 6,
        "equipment": "gym",
        "injuries": [],
        "focus_muscles": [],
    }

    response = client.post("/workout/generate", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
