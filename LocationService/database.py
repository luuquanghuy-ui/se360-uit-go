import redis.asyncio as redis
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    print(f"Đã kết nối thành công đến Redis tại {REDIS_URL}")
except Exception as e:
    print(f"Lỗi khi kết nối Redis: {e}")
    redis_client = None

DRIVER_GEO_KEY = "drivers:online"