import os

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# MongoDB configuration using environment variables with defaults
# MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
# DB_NAME = os.getenv("DB_NAME", "stockapi")
MONGO_DB_HOST = os.getenv("MONGO_DB_HOST")
MONGO_DB_PORT = os.getenv("MONGO_DB_PORT")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
MONGO_DB_USER = os.getenv("MONGO_DB_USER")

MONGO_URI = (
    f"mongodb://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_HOST}:{MONGO_DB_PORT}/{MONGO_DB_NAME}"
)


class DBMongo:
    def __init__(self):
        self.client = None
        self.db = None

    def connect(self, uri, db_name):
        """Connects to MongoDB and selects a database."""
        try:
            self.client = MongoClient(uri)
            self.client.admin.command("ping")  # Verify connection
            self.db = self.client[db_name]
            print("Successfully connected to MongoDB. ✅")
        except ConnectionFailure as e:
            print(f"Could not connect to MongoDB: {e}")
            # Handle the error appropriately (e.g., exit the app)
            raise

    def close(self):
        """Closes the MongoDB connection."""
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")


# Create a single instance of the database connection manager
db_mongo = DBMongo()
