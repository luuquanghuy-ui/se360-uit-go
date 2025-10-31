# PaymentService/crud.py (Đã sửa đổi)

import os
import hashlib
import hmac
import asyncio
import logging # <-- Thêm logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from urllib.parse import urlencode, quote_plus
from bson import ObjectId

# Import models và schemas của PaymentService
import models
import schemas

# Import các hàm lấy collection từ database.py
from database import get_wallets_collection, get_transactions_collection
from motor.motor_asyncio import AsyncIOMotorCollection

# --- Cấu hình Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Đọc biến môi trường ---
VNP_TMN_CODE = os.getenv("VNP_TMN_CODE")
VNP_HASH_SECRET = os.getenv("VNP_HASH_SECRET")
VNP_URL = os.getenv("VNP_URL")
# Bỏ đọc BASE_URL trực tiếp ở đây
# DRIVER_SERVICE_URL = os.getenv("DRIVER_SERVICE_URL")
APP_COMMISSION_RATE = 0.20

# === [HÀM MỚI] Lấy Base URL linh hoạt ===
def _get_base_url() -> str:
    """
    Xác định Base URL cho callback.
    Ưu tiên BASE_URL env, sau đó là WEBSITE_HOSTNAME (Azure), cuối cùng là localhost.
    """
    # 1. Ưu tiên biến BASE_URL nếu được đặt rõ ràng
    explicit_base_url = os.getenv("BASE_URL")
    if explicit_base_url:
        logger.info(f"Sử dụng BASE_URL được cấu hình: {explicit_base_url}")
        # Đảm bảo URL có http/https prefix
        if not explicit_base_url.startswith(("http://", "https://")):
            return f"https://{explicit_base_url}" # Mặc định https cho cấu hình rõ ràng
        return explicit_base_url

    # 2. Kiểm tra biến môi trường của Azure App Service
    azure_hostname = os.getenv("WEBSITE_HOSTNAME")
    if azure_hostname:
        base_url = f"https://{azure_hostname}"
        logger.info(f"Phát hiện môi trường Azure App Service. Sử dụng BASE_URL: {base_url}")
        return base_url

    # 3. Mặc định cho môi trường local (callback IPN sẽ không hoạt động từ bên ngoài)
    local_base_url = "http://localhost:8004" # Port của paymentservice
    logger.warning(f"Không tìm thấy BASE_URL hoặc WEBSITE_HOSTNAME. Mặc định dùng URL local: {local_base_url}. Callback IPN từ VNPAY sẽ không hoạt động.")
    return local_base_url
# === [HẾT HÀM MỚI] ===

async def process_vnpay_payment(request: schemas.ProcessPaymentRequest) -> Dict:
    """Tạo URL thanh toán VNPay."""

    # Lấy Base URL động
    base_url = _get_base_url()

    # Kiểm tra cấu hình VNPay cơ bản (không cần BASE_URL ở đây nữa)
    if not all([VNP_TMN_CODE, VNP_HASH_SECRET, VNP_URL]):
         logger.error("Lỗi: Thiếu cấu hình VNP_TMN_CODE, VNP_HASH_SECRET hoặc VNP_URL.")
         return {"status": "FAILED", "message": "Lỗi cấu hình thanh toán VNPay."}

    try:
        order_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        amount = int(request.amount) * 100
        order_desc = f'Thanh toan cho chuyen di {request.trip_id}'
        ip_addr = '127.0.0.1' # Cần lấy IP thực từ request header (X-Forwarded-For)

        # === [SỬA ĐỔI] Sử dụng base_url động ===
        # URL Khách hàng thấy sau khi thanh toán
        return_url = f"{base_url}/v1/payment/vnpay_return?order_id={order_id}&trip_id={request.trip_id}"
        # URL VNPAY gọi về server (IPN) - Rất quan trọng
        ipn_url = f"{base_url}/v1/payment/vnpay_ipn" # Endpoint này cần được tạo trong main.py
        # === [HẾT SỬA ĐỔI] ===

        vnp_params = {
            'vnp_Version': '2.1.0',
            'vnp_Command': 'pay',
            'vnp_TmnCode': VNP_TMN_CODE,
            'vnp_Amount': amount,
            'vnp_CurrCode': 'VND',
            'vnp_TxnRef': order_id,
            'vnp_OrderInfo': order_desc,
            'vnp_OrderType': 'other',
            'vnp_Locale': 'vn',
            'vnp_ReturnUrl': return_url,
            'vnp_IpAddr': ip_addr,
            'vnp_CreateDate': datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'),
            'vnp_IpnURL': ipn_url # <-- THÊM THAM SỐ IPN
        }

        sorted_params = sorted(vnp_params.items())
        hash_data_string = "&".join([
            f"{key}={quote_plus(str(value))}" for key, value in sorted_params
        ])
        h = hmac.new(VNP_HASH_SECRET.encode('utf-8'), hash_data_string.encode('utf-8'), hashlib.sha512)
        secure_hash = h.hexdigest()
        vnp_params['vnp_SecureHash'] = secure_hash
        payment_url = VNP_URL + "?" + urlencode(vnp_params, quote_via=quote_plus)

        # Lưu giao dịch PENDING (Logic cũ giữ nguyên)
        transactions_coll: Optional[AsyncIOMotorCollection] = await get_transactions_collection()
        if transactions_coll:
            pending_transaction = models.Transaction(
                transaction_id=order_id,
                user_id=request.user_id, # Đảm bảo user_id có trong ProcessPaymentRequest
                trip_id=request.trip_id,
                amount=request.amount,
                transaction_type=models.TransactionType.PAYMENT,
                payment_method="VNPAY",
                status=models.TransactionStatus.PENDING,
                vnpay_txnref=order_id
            )
            await transactions_coll.insert_one(pending_transaction.model_dump(by_alias=True, exclude={"id"}))
            logger.info(f"PaymentService: Đã lưu giao dịch PENDING {order_id} cho chuyến {request.trip_id}")
        else:
             logger.error("Lỗi: Không lấy được transactions_collection để lưu giao dịch PENDING.")
             # Ném lỗi 503 nếu không lưu được
             # raise HTTPException(status_code=503, detail="Lỗi lưu trữ giao dịch")
             # Hoặc chỉ trả về lỗi Failed
             return {"status": "FAILED", "message": "Lỗi hệ thống khi tạo giao dịch."}

        return {"status": "PENDING", "payUrl": payment_url, "transaction_id": order_id}

    except Exception as e:
        logger.error(f"Loi khi tao link VNPay: {e}", exc_info=True)
        return {"status": "FAILED", "message": "Có lỗi xảy ra khi tạo yêu cầu thanh toán."}


# --- Các hàm khác (get_or_create_wallet, top_up_driver_wallet, handle_vnpay_return) ---
# --- GIỮ NGUYÊN NHƯ CODE CŨ CỦA BẠN ---
# Lưu ý: Hàm handle_vnpay_return (xử lý IPN/Return) cũng cần được kiểm tra
#       và đảm bảo logic cộng tiền, gọi TripService hoạt động đúng.

async def get_or_create_wallet(driver_id: str) -> Optional[Dict[str, Any]]:
    # ... (Giữ nguyên code của bạn) ...
    wallets_coll: Optional[AsyncIOMotorCollection] = await get_wallets_collection()
    if not wallets_coll:
        logger.error("Lỗi: Không lấy được wallets_collection trong get_or_create_wallet")
        return None
    wallet_data = await wallets_coll.find_one({"driver_id": driver_id})
    if not wallet_data:
        logger.info(f"PaymentService: Tạo ví mới cho tài xế {driver_id}")
        new_wallet = models.DriverWallet(driver_id=driver_id)
        insert_data = new_wallet.model_dump(by_alias=True, exclude={"id"})
        await wallets_coll.insert_one(insert_data)
        wallet_data = await wallets_coll.find_one({"driver_id": driver_id})
    if wallet_data and "_id" in wallet_data:
        wallet_data["_id"] = str(wallet_data["_id"])
    return wallet_data


async def top_up_driver_wallet(request: schemas.TopUpRequest) -> Optional[Dict[str, Any]]:
    # ... (Giữ nguyên code của bạn, chỉ thêm logger) ...
    wallets_coll: Optional[AsyncIOMotorCollection] = await get_wallets_collection()
    transactions_coll: Optional[AsyncIOMotorCollection] = await get_transactions_collection()
    if not wallets_coll or not transactions_coll:
        logger.error("Lỗi: Không lấy được collection trong top_up_driver_wallet")
        return None
    wallet = await get_or_create_wallet(request.driver_id)
    if not wallet: return None
    update_result = await wallets_coll.update_one(
        {"driver_id": request.driver_id},
        {"$inc": {"balance": request.amount}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    if update_result.modified_count == 1:
        top_up_transaction = models.Transaction(
            user_id=request.driver_id,
            transaction_type=models.TransactionType.TOPUP,
            amount=request.amount,
            status=models.TransactionStatus.SUCCESS,
            description=request.note
        )
        await transactions_coll.insert_one(top_up_transaction.model_dump(by_alias=True, exclude={"id"}))
        updated_wallet = await wallets_coll.find_one({"driver_id": request.driver_id})
        if updated_wallet and "_id" in updated_wallet:
            updated_wallet["_id"] = str(updated_wallet["_id"])
        return updated_wallet
    else:
        logger.error(f"Lỗi khi cập nhật số dư cho ví của tài xế {request.driver_id}")
        return None

async def handle_vnpay_return(vnpay_response_data: Dict[str, Any]) -> bool: 
    transactions_coll: Optional[AsyncIOMotorCollection] = await get_transactions_collection()
    if not transactions_coll: return False

    # --- [QUAN TRỌNG] KIỂM TRA SECURE HASH ---
    input_params = {k: v for k, v in vnpay_response_data.items() if k.startswith('vnp_') and k != 'vnp_SecureHash'}
    received_secure_hash = vnpay_response_data.get('vnp_SecureHash')

    # Sắp xếp lại và tạo chuỗi hash data từ response
    sorted_params = sorted(input_params.items())
    hash_data_string = "&".join([
        f"{key}={quote_plus(str(value))}" for key, value in sorted_params
    ])

    # Tạo chữ ký từ server side
    h = hmac.new(VNP_HASH_SECRET.encode('utf-8'), hash_data_string.encode('utf-8'), hashlib.sha512)
    calculated_secure_hash = h.hexdigest()

    if calculated_secure_hash != received_secure_hash:
        logger.error(f"VNPay Callback: Sai Secure Hash! Giao dịch có thể không hợp lệ. TxnRef: {vnpay_response_data.get('vnp_TxnRef')}")
        return False
    else:
        logger.info(f"VNPay Callback: Secure Hash hợp lệ. TxnRef: {vnpay_response_data.get('vnp_TxnRef')}")
    # --- [HẾT PHẦN KIỂM TRA] ---


    order_id = vnpay_response_data.get('vnp_TxnRef')
    vnp_transaction_no = vnpay_response_data.get('vnp_TransactionNo')
    vnp_response_code = vnpay_response_data.get('vnp_ResponseCode')
    if not order_id: return False

    transaction = await transactions_coll.find_one({"transaction_id": order_id, "status": models.TransactionStatus.PENDING})
    if not transaction:
        logger.warning(f"PaymentService: Không tìm thấy giao dịch PENDING {order_id} hoặc đã xử lý.")
        # Kiểm tra xem có phải đã SUCCESS không (do IPN chạy trước)
        existing = await transactions_coll.find_one({"transaction_id": order_id})
        return existing is not None # Trả về True nếu giao dịch đã tồn tại (đã xử lý)

    new_status = models.TransactionStatus.FAILED
    if vnp_response_code == '00':
        new_status = models.TransactionStatus.SUCCESS
        # === [THÊM LOGIC TÍNH TOÁN VÀ CỘNG TIỀN CHO TÀI XẾ] ===
        trip_id = transaction.get("trip_id")
        # Lấy số tiền gốc khách hàng trả (đã lưu trong transaction)
        total_fare = transaction.get("amount")

        if trip_id and total_fare:
            # Gọi TripService lấy chi tiết chuyến đi (để lấy driver_id)
            trip_details = await get_trip_details(trip_id)

            if trip_details and trip_details.get("driver_id"):
                driver_id = trip_details["driver_id"]
                # Lấy cước phí thực tế từ TripService nếu có (chính xác hơn)
                actual_fare_from_trip = trip_details.get("fare", {}).get("actual")
                fare_to_process = actual_fare_from_trip if actual_fare_from_trip else total_fare

                # Tính toán hoa hồng và thu nhập tài xế
                commission = fare_to_process * APP_COMMISSION_RATE
                driver_earning = fare_to_process - commission
                logger.info(f"Chuyến {trip_id}: Cước {fare_to_process}, Hoa hồng {commission}, Tài xế {driver_id} nhận {driver_earning}")

                # Gọi hàm cộng tiền vào ví tài xế
                credit_success = await credit_driver_wallet(driver_id, driver_earning, trip_id)
                if not credit_success:
                     logger.error(f"Lỗi nghiêm trọng: Không thể cộng tiền cho tài xế {driver_id} (chuyến {trip_id}) sau khi thanh toán thành công.")
                     # Cần có cơ chế xử lý lỗi này (ví dụ: retry, báo cáo...)
            else:
                 logger.error(f"Không thể lấy driver_id hoặc chi tiết cho chuyến {trip_id} để cộng tiền.")
        else:
             logger.error(f"Thiếu trip_id hoặc amount trong transaction {order_id} để xử lý doanh thu.")
        # === [HẾT PHẦN LOGIC THÊM] ===
        
    update_result = await transactions_coll.update_one(
        {"transaction_id": order_id, "status": models.TransactionStatus.PENDING}, # Thêm status PENDING vào query
        {"$set": {
            "status": new_status,
            "vnpay_response_code": vnp_response_code,
            "vnpay_transaction_no": vnp_transaction_no,
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    if update_result.modified_count == 1:
        logger.info(f"PaymentService: Đã cập nhật giao dịch {order_id} thành {new_status}")
        # Gọi TripService lần nữa nếu là SUCCESS (đã làm ở trên)
        return True
    else:
        logger.error(f"PaymentService: Lỗi khi cập nhật giao dịch {order_id} (có thể đã được IPN xử lý trước).")
        # Kiểm tra lại xem có phải đã SUCCESS không
        check_again = await transactions_coll.find_one({"transaction_id": order_id, "status": models.TransactionStatus.SUCCESS})
        return check_again is not None # Trả về True nếu nó đã Success rồi

# === [THÊM HÀM HELPER GỌI TRIP SERVICE] ===
async def notify_trip_service_payment_status(trip_id: str, transaction_id: str, status: models.TransactionStatus):
    """Gọi TripService để cập nhật trạng thái thanh toán của chuyến đi."""
    TRIP_SERVICE_URL = os.getenv("TRIP_SERVICE_URL") # Đọc URL TripService
    if not TRIP_SERVICE_URL:
        logger.error("TRIP_SERVICE_URL chưa được cấu hình. Không thể thông báo trạng thái thanh toán.")
        return

    # Endpoint này cần được tạo bên TripService
    url = f"{TRIP_SERVICE_URL}/trips/{trip_id}/payment" 
    payload = {
        "status": status.value, # "SUCCESS" hoặc "FAILED"
        "transaction_id": transaction_id
        # Có thể thêm paid_at nếu cần
        # "paid_at": datetime.now(timezone.utc).isoformat() if status == models.TransactionStatus.SUCCESS else None
    }
    
    logger.info(f"Đang thông báo trạng thái thanh toán ({status.value}) cho TripService (chuyến {trip_id})...")
    try:
        async with httpx.AsyncClient() as client:
            # Dùng PUT để cập nhật
            response = await client.put(url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Thông báo trạng thái thanh toán cho TripService thành công.")
    except httpx.RequestError as e:
        logger.error(f"Lỗi kết nối đến TripService để thông báo thanh toán: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"TripService trả lỗi khi cập nhật thanh toán: {e.response.status_code} - {e.response.text}")
    except Exception as e:
         logger.error(f"Lỗi không xác định khi thông báo thanh toán cho TripService: {e}")

# (Bạn có thể cần thêm các hàm helper khác như credit_driver_wallet nếu logic đó nằm ở đây)
# === [THÊM 2 HÀM HELPER MỚI NÀY] ===

async def get_trip_details(trip_id: str) -> Optional[Dict[str, Any]]:
    """Gọi TripService để lấy thông tin chi tiết chuyến đi."""
    if not TRIP_SERVICE_URL:
        logger.error("TRIP_SERVICE_URL chưa được cấu hình. Không thể lấy chi tiết chuyến đi.")
        return None

    url = f"{TRIP_SERVICE_URL}/trips/{trip_id}"
    logger.info(f"Đang gọi TripService để lấy chi tiết chuyến đi {trip_id} tại {url}...")
    try:
        async with httpx.AsyncClient() as client:
            # Giả sử API này không cần xác thực đặc biệt khi gọi nội bộ
            # Nếu cần Service Token, bạn cần thêm logic lấy token tương tự TripService
            response = await client.get(url, timeout=5.0)
            response.raise_for_status() 
            trip_data = response.json()
            logger.info(f"Lấy chi tiết chuyến đi {trip_id} thành công.")
            return trip_data
    except httpx.RequestError as e:
        logger.error(f"Lỗi kết nối đến TripService để lấy chi tiết chuyến đi: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"TripService trả lỗi khi lấy chi tiết chuyến đi: {e.response.status_code} - {e.response.text}")
    except Exception as e:
         logger.error(f"Lỗi không xác định khi lấy chi tiết chuyến đi: {e}")
    return None

async def credit_driver_wallet(driver_id: str, amount: float, trip_id: str) -> bool:
    """Cộng tiền vào ví tài xế (do PaymentService quản lý) và ghi log giao dịch."""
    wallets_coll: Optional[AsyncIOMotorCollection] = await get_wallets_collection()
    transactions_coll: Optional[AsyncIOMotorCollection] = await get_transactions_collection()
    if not wallets_coll or not transactions_coll:
        logger.error(f"Không lấy được collection trong credit_driver_wallet cho driver {driver_id}")
        return False

    # Lấy hoặc tạo ví
    wallet = await get_or_create_wallet(driver_id)
    if not wallet:
        logger.error(f"Không thể lấy hoặc tạo ví cho driver {driver_id} để cộng tiền.")
        return False

    # Thực hiện cộng tiền
    try:
        update_result = await wallets_coll.update_one(
            {"driver_id": driver_id},
            {"$inc": {"balance": amount}, "$set": {"updated_at": datetime.now(timezone.utc)}}
        )

        if update_result.modified_count == 1:
            # Ghi lại giao dịch EARNING (Thu nhập)
            earning_transaction = models.Transaction(
                user_id=driver_id, # Giao dịch thuộc về tài xế
                trip_id=trip_id,
                transaction_type=models.TransactionType.EARNING, # Loại giao dịch mới
                amount=amount, # Số tiền tài xế thực nhận
                status=models.TransactionStatus.SUCCESS,
                description=f"Thu nhập từ chuyến đi {trip_id}"
            )
            await transactions_coll.insert_one(earning_transaction.model_dump(by_alias=True, exclude={"id"}))
            logger.info(f"Đã cộng {amount} vào ví tài xế {driver_id} cho chuyến {trip_id}.")
            return True
        else:
            logger.error(f"Lỗi không mong muốn: Không thể cập nhật số dư cho ví của tài xế {driver_id} (modified_count=0).")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi cộng tiền vào ví tài xế {driver_id}: {e}", exc_info=True)
        return False
# === [HẾT PHẦN THÊM] ===


