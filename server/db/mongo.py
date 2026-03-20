# MongoDB connection module.
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

# Create MongoDB client
client = MongoClient(MONGO_URI)

# Select database
db = client[DB_NAME]

# Collections
users_collection = db["users"]
meal_plans_collection = db["meal_plans"]
workout_plans_collection = db["workout_plans"]
progress_logs_collection = db["progress_logs"]
chat_history_collection = db["chat_history"]

# testing connection
def test_connection():
    try:
        client.admin.command('ping')
        print("MongoDB Connected Successfully")
    except Exception as e:
        print(" MongoDB Connection Failed:", e)
# Provides database instance for all services and controllers.
