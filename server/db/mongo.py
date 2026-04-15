"""MongoDB connection module."""

from pymongo import MongoClient
from config import MONGO_URI, DB_NAME


if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not configured. Set it in server/.env")

# Keep server selection timeout short so startup/checks fail fast when DB is unreachable.
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

# Select database
db = client[DB_NAME]

# Collections
users_collection = db["users"]
meal_plans_collection = db["meal_plans"]
workout_plans_collection = db["workout_plans"]
progress_logs_collection = db["progress_logs"]
chat_history_collection = db["chat_history"]

def test_connection(raise_on_error=False):
    """Ping MongoDB and return True on success.

    Args:
        raise_on_error: Re-raise the original exception when connection fails.
    """
    try:
        client.admin.command("ping")
        return True
    except Exception:
        if raise_on_error:
            raise
        return False
