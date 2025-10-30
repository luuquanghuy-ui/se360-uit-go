import redis.asyncio as redis
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_KEY = os.getenv("REDIS_KEY", None)
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

try:
    if REDIS_KEY:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_KEY, ssl=True, decode_responses=True)
    else:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
    print(f"Đã kết nối thành công đến Redis tại {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    print(f"Lỗi khi kết nối Redis: {e}")
    redis_client = None

DRIVER_GEO_KEY = "drivers:online"