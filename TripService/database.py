import os
import motor.motor_asyncio
from pymongo import MongoClient

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("MONGO_INITDB_DATABASE", "uitgo_trips")

if not MONGODB_URL:
    raise ValueError("LỖI: Không đọc được MONGODB_URL từ docker-compose.yml.")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]

trips_collection = database.get_collection("trips")
ratings_collection = database.get_collection("ratings")

sync_client = MongoClient(MONGODB_URL)
sync_database = sync_client[DATABASE_NAME]

def get_database():
    return database