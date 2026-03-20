# load the db uri
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "metameal_db"
# Loads environment variables and stores application-level constants.
