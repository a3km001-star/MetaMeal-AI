# load the db uri
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "metameal_db"
JWT_SECRET = os.getenv("JWT_SECRET", "replace-this-with-a-secure-value")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
PASSWORD_HASH_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "100000"))
GROQ_API_KEY=os.getenv("GROQ_API_KEY")
# Loads environment variables and stores application-level constants.
