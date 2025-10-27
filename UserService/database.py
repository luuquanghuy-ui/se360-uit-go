import os
import logging
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

DB_NAME = os.getenv("MONGO_INITDB_DATABASE", "uitgo_users")


_client: AsyncIOMotorClient | None = None

async def get_db_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        logger.info(f"UserService: Đang khởi tạo kết nối đến MongoDB tại {MONGODB_URL}...")
        try:
            _client = AsyncIOMotorClient(MONGODB_URL)
            await _client.admin.command('ping')
            logger.info(f"UserService: Kết nối MongoDB thành công!")
        except Exception as e:
            logger.error(f"UserService: LỖI kết nối MongoDB: {e}")
            _client = None
            raise 
    return _client

async def get_database() -> AsyncIOMotorDatabase | None:
    try:
        client = await get_db_client()
        if client is not None:
            return client[DB_NAME]
        else:
            logger.error("UserService: Không thể lấy database vì client là None.")
            return None
    except Exception as e:
        logger.error(f"UserService: Lỗi khi lấy database: {e}")
        return None

async def get_users_collection() -> AsyncIOMotorCollection | None:
    db = await get_database()
    if db is not None: 
        return db.get_collection("users")
    return None

async def create_indexes():
    users_collection = await get_users_collection()
    if users_collection is not None:
        try:
            await users_collection.create_index("email", unique=True, background=True)
            await users_collection.create_index("phone", unique=True, sparse=True, background=True)
            logger.info("UserService: Đã tạo/đảm bảo các index cho collection 'users'.")
        except Exception as e:
            logger.error(f"UserService: Lỗi khi tạo index: {e}")
    else:
        logger.warning("UserService: Không thể tạo index vì không lấy được users_collection.")