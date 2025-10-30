# DriverService/database.py
import os
import motor.motor_asyncio
from dotenv import load_dotenv
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGODB_URL = os.getenv("MONGODB_URL") 
DB_NAME = os.getenv("MONGO_INITDB_DATABASE", "uitgo_drivers") 

if not MONGODB_URL:
    logger.error("DriverService: Lỗi nghiêm trọng - Không tìm thấy biến môi trường MONGODB_URL.")
    raise ValueError("Lỗi: Không tìm thấy MONGODB_URL.")

try:
    logger.info(f"DriverService: Đang khởi tạo kết nối đến MongoDB tại {MONGODB_URL}...")
    client: AsyncIOMotorClient = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
    database: AsyncIOMotorDatabase = client[DB_NAME]
    
    drivers_collection: AsyncIOMotorCollection = database.get_collection("drivers")
    driver_wallets_collection: AsyncIOMotorCollection = database.get_collection("driver_wallets")

    logger.info(f"DriverService: Kết nối MongoDB thành công! DB: {DB_NAME}")

except Exception as e:
    logger.error(f"DriverService: LỖI kết nối MongoDB khi khởi tạo: {e}")
    client = None
    database = None
    drivers_collection = None
    driver_wallets_collection = None

async def create_driver_indexes():
    """Tạo các index cần thiết (gọi khi startup)."""
    if drivers_collection is None or driver_wallets_collection is None:
        logger.warning("DriverService: Không thể tạo index vì kết nối DB thất bại.")
        return
    try:
        await drivers_collection.create_index("phone", unique=True, sparse=True, background=True)
        await drivers_collection.create_index("email", unique=True, sparse=True, background=True)
        await driver_wallets_collection.create_index("driver_id", unique=True, background=True)
        
        logger.info("DriverService: Đã tạo/đảm bảo index.")
    except Exception as e:
        logger.error(f"DriverService: Lỗi tạo index: {e}")