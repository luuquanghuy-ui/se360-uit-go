# PaymentService/database.py
import os
import motor.motor_asyncio
from dotenv import load_dotenv
import logging
# Import trực tiếp các kiểu dữ liệu
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Đọc URL MongoDB từ biến môi trường
MONGODB_URL = os.getenv("MONGODB_URL")
DB_NAME = os.getenv("MONGO_INITDB_DATABASE", "uitgo_payments")

if not MONGODB_URL:
    logger.error("PaymentService: Lỗi nghiêm trọng - Không tìm thấy biến môi trường MONGODB_URL.")
    raise ValueError("Lỗi: Không tìm thấy MONGODB_URL. Hãy kiểm tra biến môi trường.")

# --- KHỞI TẠO CLIENT Ở CẤP ĐỘ MODULE ---
try:
    logger.info(f"PaymentService: Đang khởi tạo kết nối đến MongoDB tại {MONGODB_URL}...")
    client: AsyncIOMotorClient = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)

    database: AsyncIOMotorDatabase = client[DB_NAME]
    

    logger.info(f"PaymentService: Kết nối MongoDB thành công! DB: {DB_NAME}")

except Exception as e:
    logger.error(f"PaymentService: LỖI kết nối MongoDB khi khởi tạo: {e}")
    # Đặt client và database thành None nếu lỗi để các hàm sau biết
    client = None
    database = None

# --- CÁC HÀM LẤY COLLECTION ---
# Các hàm này giờ chỉ cần kiểm tra xem database có None không

async def get_wallets_collection() -> AsyncIOMotorCollection:
    """Lấy collection 'wallets'."""
    if database is None:
        raise Exception("PaymentService: Database chưa được khởi tạo thành công.")
    return database.get_collection("wallets")

async def get_transactions_collection() -> AsyncIOMotorCollection:
    """Lấy collection 'transactions'."""
    if database is None:
        raise Exception("PaymentService: Database chưa được khởi tạo thành công.")
    return database.get_collection("transactions")

# --- HÀM TẠO INDEX (Vẫn cần gọi khi startup) ---
async def create_payment_indexes():
    """Tạo các index cần thiết (nên gọi khi ứng dụng khởi động)."""
    if database is None:
        logger.warning("PaymentService: Không thể tạo index vì kết nối DB thất bại.")
        return
    try:
        wallets_coll = await get_wallets_collection() # Gọi hàm get để chắc chắn db không None
        await wallets_coll.create_index("driver_id", unique=True, background=True)
        
        transactions_coll = await get_transactions_collection()
        await transactions_coll.create_index("trip_id", background=True)
        # Thêm index khác nếu cần (ví dụ: status, created_at cho transaction)
        
        logger.info("PaymentService: Đã tạo/đảm bảo index.")
    except Exception as e:
        logger.error(f"PaymentService: Lỗi tạo index: {e}")