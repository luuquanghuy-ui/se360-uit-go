# PaymentService/crud.py

import os
import hashlib
import hmac
import asyncio
from datetime import datetime, timezone # Thêm timezone
from typing import Dict, Optional, Any # Thêm Optional, Any
from urllib.parse import urlencode, quote_plus
from bson import ObjectId # Thêm ObjectId nếu bạn dùng ID của MongoDB

# Import models và schemas của PaymentService
import models
import schemas

# --- Sửa cách import database ---
# from database import wallets_collection, transactions_collection # <-- Dòng cũ
from database import get_wallets_collection, get_transactions_collection # <-- Dòng mới (import hàm)
from motor.motor_asyncio import AsyncIOMotorCollection # <-- Thêm import kiểu dữ liệu

# --- Đọc biến môi trường ---
VNP_TMN_CODE = os.getenv("VNP_TMN_CODE")
VNP_HASH_SECRET = os.getenv("VNP_HASH_SECRET")
VNP_URL = os.getenv("VNP_URL")
BASE_URL = os.getenv("BASE_URL") # Hoặc NGROK_API_URL nếu bạn lấy động
# DRIVER_SERVICE_URL = os.getenv("DRIVER_SERVICE_URL") # Bỏ comment nếu cần gọi DriverService
APP_COMMISSION_RATE = 0.20 # Tỷ lệ hoa hồng (ví dụ)

async def process_vnpay_payment(request: schemas.ProcessPaymentRequest) -> Dict:
    """Tạo URL thanh toán VNPay."""
    # Hàm này chủ yếu xử lý logic VNPay, không cần truy cập DB trực tiếp ở đây
    # (Trừ khi bạn muốn lưu lại thông tin giao dịch PENDING trước khi tạo URL)
    
    # Kiểm tra các biến môi trường VNPay
    if not all([VNP_TMN_CODE, VNP_HASH_SECRET, VNP_URL, BASE_URL]):
         print("Lỗi: Thiếu cấu hình VNPay hoặc BASE_URL.")
         return {"status": "FAILED", "message": "Lỗi cấu hình thanh toán."}

    try:
        # Tạo mã giao dịch duy nhất
        order_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") # Thêm microsecond cho unique
        amount = int(request.amount) * 100 # VNPay dùng đơn vị xu
        order_desc = f'Thanh toan cho chuyen di {request.trip_id}'
        ip_addr = '127.0.0.1' # Lấy IP thực tế từ request nếu có thể
        # URL VNPay sẽ gọi về sau khi thanh toán
        # Cần thêm tham số để biết giao dịch nào, ví dụ: ?order_id={order_id}&trip_id={request.trip_id}
        return_url = f"{BASE_URL}/v1/payment/vnpay_return?order_id={order_id}&trip_id={request.trip_id}" 

        # Tạo dictionary chứa các tham số VNPay
        vnp_params = {
            'vnp_Version': '2.1.0',
            'vnp_Command': 'pay',
            'vnp_TmnCode': VNP_TMN_CODE,
            'vnp_Amount': amount,
            'vnp_CurrCode': 'VND',
            'vnp_TxnRef': order_id, # Mã tham chiếu giao dịch của bạn
            'vnp_OrderInfo': order_desc,
            'vnp_OrderType': 'other', # Loại hàng hóa
            'vnp_Locale': 'vn', # Ngôn ngữ
            'vnp_ReturnUrl': return_url, # URL trả về
            'vnp_IpAddr': ip_addr, # IP người dùng
            'vnp_CreateDate': datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') # Ngày tạo GD
            # Thêm vnp_ExpireDate nếu muốn giới hạn thời gian thanh toán
            # 'vnp_ExpireDate': (datetime.now(timezone.utc) + timedelta(minutes=15)).strftime('%Y%m%d%H%M%S') 
        }

        # Sắp xếp tham số theo alphabet
        sorted_params = sorted(vnp_params.items())
        
        # Tạo chuỗi hash data
        hash_data_string = "&".join([
            f"{key}={quote_plus(str(value))}" for key, value in sorted_params
        ])
        
        # Tạo chữ ký bảo mật
        h = hmac.new(VNP_HASH_SECRET.encode('utf-8'), hash_data_string.encode('utf-8'), hashlib.sha512)
        secure_hash = h.hexdigest()

        # Thêm chữ ký vào tham số
        vnp_params['vnp_SecureHash'] = secure_hash

        # Tạo URL thanh toán hoàn chỉnh
        payment_url = VNP_URL + "?" + urlencode(vnp_params, quote_via=quote_plus)

        # (Quan trọng) Lưu lại thông tin giao dịch PENDING vào MongoDB
        # Lấy collection transactions
        transactions_coll: AsyncIOMotorCollection = await get_transactions_collection()
        if transactions_coll:
             # Tạo document giao dịch
             pending_transaction = models.Transaction(
                 transaction_id=order_id, # Dùng mã vnp_TxnRef làm ID giao dịch
                 user_id=request.user_id, # Thêm user_id vào schema ProcessPaymentRequest
                 trip_id=request.trip_id,
                 amount=request.amount, # Lưu số tiền gốc (không nhân 100)
                 transaction_type=models.TransactionType.PAYMENT,
                 payment_method="VNPAY", # Hoặc lấy từ request nếu có nhiều cổng
                 status=models.TransactionStatus.PENDING,
                 vnpay_txnref=order_id # Lưu lại mã TxnRef của VNPay
             )
             # Lưu vào DB
             await transactions_coll.insert_one(pending_transaction.model_dump(by_alias=True, exclude={"id"}))
             print(f"PaymentService: Đã lưu giao dịch PENDING {order_id} cho chuyến {request.trip_id}")
        else:
             print("Lỗi: Không lấy được transactions_collection để lưu giao dịch PENDING.")
             # Có thể ném lỗi ở đây nếu việc lưu là bắt buộc
             # raise HTTPException(status_code=503, detail="Lỗi lưu trữ giao dịch")


        # Trả về URL cho client redirect
        return {"status": "PENDING", "payUrl": payment_url, "transaction_id": order_id}

    except Exception as e:
        print(f"Loi khi tao link VNPay: {e}")
        return {"status": "FAILED", "message": "Có lỗi xảy ra khi tạo yêu cầu thanh toán."}


async def get_or_create_wallet(driver_id: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin ví của tài xế, tạo mới nếu chưa có."""
    # Lấy collection wallets bằng cách gọi hàm async
    wallets_coll: AsyncIOMotorCollection = await get_wallets_collection()
    if not wallets_coll:
        print("Lỗi: Không lấy được wallets_collection trong get_or_create_wallet")
        return None # Hoặc ném Exception

    # Tìm ví trong DB
    wallet_data = await wallets_coll.find_one({"driver_id": driver_id})

    # Nếu không tìm thấy, tạo ví mới
    if not wallet_data:
        print(f"PaymentService: Tạo ví mới cho tài xế {driver_id}")
        new_wallet = models.DriverWallet(driver_id=driver_id) # Dùng model DriverWallet từ models.py
        # Chuyển thành dict để lưu, by_alias=True để dùng _id (nếu có)
        insert_data = new_wallet.model_dump(by_alias=True, exclude={"id"}) 
        await wallets_coll.insert_one(insert_data)
        # Lấy lại thông tin ví vừa tạo
        wallet_data = await wallets_coll.find_one({"driver_id": driver_id})

    # Trả về dữ liệu ví (dạng dictionary)
    if wallet_data and "_id" in wallet_data:
         wallet_data["_id"] = str(wallet_data["_id"]) # Chuyển ObjectId sang string
    return wallet_data


async def top_up_driver_wallet(request: schemas.TopUpRequest) -> Optional[Dict[str, Any]]:
    """Nạp tiền vào ví tài xế."""
    # Lấy collection wallets và transactions
    wallets_coll: AsyncIOMotorCollection = await get_wallets_collection()
    transactions_coll: AsyncIOMotorCollection = await get_transactions_collection()
    if not wallets_coll or not transactions_coll:
        print("Lỗi: Không lấy được collection trong top_up_driver_wallet")
        return None

    # Lấy hoặc tạo ví cho tài xế
    wallet = await get_or_create_wallet(request.driver_id) # Giả sử schema TopUpRequest có driver_id
    if not wallet:
         return None # Lỗi đã được log ở hàm get_or_create_wallet

    # Cập nhật số dư trong MongoDB
    update_result = await wallets_coll.update_one(
        {"driver_id": request.driver_id},
        # Dùng $inc để cộng tiền, $set để cập nhật thời gian
        {"$inc": {"balance": request.amount}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )

    if update_result.modified_count == 1:
        # Ghi lại giao dịch nạp tiền
        top_up_transaction = models.Transaction(
            # wallet_id=str(wallet["_id"]), # ID của ví
            user_id=request.driver_id, # Lưu ID của người thực hiện (có thể là admin?) hoặc driver_id
            transaction_type=models.TransactionType.TOPUP,
            amount=request.amount,
            status=models.TransactionStatus.SUCCESS,
            description=request.note # Thêm description từ request
        )
        await transactions_coll.insert_one(top_up_transaction.model_dump(by_alias=True, exclude={"id"}))

        # Lấy lại thông tin ví đã cập nhật để trả về
        updated_wallet = await wallets_coll.find_one({"driver_id": request.driver_id})
        if updated_wallet and "_id" in updated_wallet:
            updated_wallet["_id"] = str(updated_wallet["_id"])
        return updated_wallet
    else:
        print(f"Lỗi khi cập nhật số dư cho ví của tài xế {request.driver_id}")
        return None

# === CÁC HÀM XỬ LÝ KẾT QUẢ VNPay (Ví dụ) ===

async def handle_vnpay_return(vnpay_response_data: Dict[str, Any]) -> bool:
     """Xử lý kết quả trả về từ VNPay, cập nhật trạng thái giao dịch."""
     transactions_coll: AsyncIOMotorCollection = await get_transactions_collection()
     if not transactions_coll: return False
     
     # Lấy mã giao dịch của bạn từ response VNPay
     order_id = vnpay_response_data.get('vnp_TxnRef')
     # Lấy mã giao dịch của VNPay
     vnp_transaction_no = vnpay_response_data.get('vnp_TransactionNo')
     # Lấy mã phản hồi
     vnp_response_code = vnpay_response_data.get('vnp_ResponseCode')
     
     if not order_id: return False # Thiếu thông tin cần thiết
     
     # Kiểm tra chữ ký bảo mật của VNPay (quan trọng!)
     # ... (code kiểm tra chữ ký ở đây) ...
     
     # Tìm giao dịch PENDING trong DB
     transaction = await transactions_coll.find_one({"transaction_id": order_id, "status": models.TransactionStatus.PENDING})
     
     if not transaction:
         print(f"PaymentService: Không tìm thấy giao dịch PENDING {order_id} hoặc đã xử lý.")
         # Có thể là IPN gọi trước hoặc lỗi logic
         return False # Hoặc True nếu đã xử lý rồi

     new_status = models.TransactionStatus.FAILED # Mặc định là thất bại
     if vnp_response_code == '00': # Mã 00 là thành công
          new_status = models.TransactionStatus.SUCCESS
          
          # --- CỘNG TIỀN VÀO VÍ TÀI XẾ (Nếu là thanh toán chuyến đi) ---
          # (Logic này phức tạp hơn, cần xác định ai nhận tiền)
          # Ví dụ: Cộng tiền vào ví tài xế sau khi trừ hoa hồng
          # trip_id = transaction.get("trip_id")
          # driver_id = ... # Cần lấy driver_id từ TripService hoặc từ transaction
          # amount_received = transaction.get("amount") * (1 - APP_COMMISSION_RATE)
          # await credit_driver_wallet(driver_id, amount_received, trip_id) 
          
     # Cập nhật trạng thái giao dịch trong DB
     update_result = await transactions_coll.update_one(
         {"transaction_id": order_id},
         {"$set": {
             "status": new_status, 
             "vnpay_response_code": vnp_response_code,
             "vnpay_transaction_no": vnp_transaction_no, # Lưu mã GD của VNPay
             "updated_at": datetime.now(timezone.utc)
         }}
     )
     
     if update_result.modified_count == 1:
         print(f"PaymentService: Đã cập nhật giao dịch {order_id} thành {new_status}")
         # Nếu thành công, có thể cần gọi sang TripService để cập nhật trạng thái thanh toán của chuyến đi
         # if new_status == models.TransactionStatus.SUCCESS:
         #     trip_id = transaction.get("trip_id")
         #     await notify_trip_service_payment_success(trip_id, order_id)
         return True
     else:
         print(f"PaymentService: Lỗi khi cập nhật giao dịch {order_id}")
         return False

# (Thêm các hàm cần thiết khác: rút tiền, xử lý IPN, gọi TripService...)
# async def credit_driver_wallet(driver_id: str, amount: float, trip_id: str): ...
# async def notify_trip_service_payment_success(trip_id: str, transaction_id: str): ...