# PaymentService/main.py (Đã sửa đổi)

import os
import hashlib
import hmac
import logging
from fastapi import FastAPI, HTTPException, status, Request, Depends # <-- Thêm Request, Depends
from typing import List, AsyncGenerator, Dict, Any # <-- Thêm AsyncGenerator, Dict, Any
from urllib.parse import parse_qsl, quote_plus
from contextlib import asynccontextmanager # <-- Thêm asynccontextmanager

# Import từ các file khác trong PaymentService
import crud
import schemas
import models
# --- Sửa cách import database và thêm hàm tạo index ---
from database import create_payment_indexes, get_wallets_collection, get_transactions_collection

# --- Cấu hình Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- LIFESPAN MANAGER (Để tạo Index khi khởi động) ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("PaymentService: Đang khởi động...")
    # Gọi hàm tạo index khi startup
    await create_payment_indexes()
    logger.info("PaymentService: Khởi động hoàn tất.")
    yield # Ứng dụng chạy ở đây
    logger.info("PaymentService: Đang tắt...")
    # (Không cần đóng kết nối MongoDB rõ ràng với motor)
    logger.info("PaymentService: Tắt hoàn tất.")

# --- KHỞI TẠO FASTAPI APP VỚI LIFESPAN ---
app = FastAPI(
    title="UIT-Go Payment Service",
    description="Microservice để xử lý thanh toán.",
    version="1.1.0",
    lifespan=lifespan # <-- Thêm lifespan
)

# --- Các biến và hằng số (Giữ nguyên) ---
APP_COMMISSION_RATE = 0.20
# DRIVER_SERVICE_URL = os.getenv("DRIVER_SERVICE_URL") # Chỉ cần trong crud.py

# === ENDPOINTS CHO VÍ (WALLET) ===
# (Đổi tên hàm crud được gọi)

@app.get("/v1/wallets/{driver_id}", response_model=schemas.WalletResponse, tags=["Wallet"])
async def get_driver_wallet_endpoint(driver_id: str):
    """Lấy thông tin ví của tài xế."""
    wallet = await crud.get_or_create_wallet(driver_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Không tìm thấy ví cho tài xế này.")
    # crud.get_or_create_wallet trả về dict, FastAPI tự convert sang WalletResponse
    return wallet

@app.post("/v1/wallets/top-up", response_model=schemas.WalletResponse, tags=["Wallet"])
async def top_up_driver_wallet_endpoint(request: schemas.TopUpRequest):
    """Nạp tiền vào ví tài xế (Ví dụ: admin nạp)."""
    updated_wallet = await crud.top_up_driver_wallet(request) # <-- Sửa tên hàm crud
    if not updated_wallet:
        raise HTTPException(status_code=500, detail="Lỗi khi nạp tiền vào ví.")
    return updated_wallet

# === ENDPOINTS CHO THANH TOÁN (PAYMENT) ===

@app.post("/v1/payment/process", response_model=schemas.PaymentLinkResponse, tags=["Payment"])
async def handle_payment_processing(request: schemas.ProcessPaymentRequest):
    """
    Endpoint chính để TripService gọi khi cần tạo link thanh toán VNPay.
    """
    logger.info(f"Nhận yêu cầu xử lý thanh toán cho chuyến đi: {request.trip_id}")
    # Gọi hàm crud đã sửa (đổi tên cho khớp)
    result = await crud.process_vnpay_payment(request) # <-- Sửa tên hàm crud

    if result.get("status") == "FAILED":
        logger.error(f"Lỗi khi tạo link VNPay: {result.get('message')}")
        raise HTTPException(
            status_code=500, # Lỗi server vì không tạo được link
            detail=result.get("message", "Lỗi không xác định khi xử lý thanh toán")
        )

    # Trả về link thanh toán và transaction_id
    return result

# === [ENDPOINT MỚI QUAN TRỌNG] XỬ LÝ IPN TỪ VNPAY ===
@app.get("/v1/payment/vnpay_ipn", tags=["VNPay Callback"])
async def handle_vnpay_ipn(request: Request):
    """
    Endpoint nhận Instant Payment Notification (IPN) từ server VNPay.
    Đây là nơi đáng tin cậy nhất để cập nhật trạng thái giao dịch.
    VNPay gửi IPN bằng GET request với các tham số trong query string.
    """
    ipn_data = dict(request.query_params)
    vnp_txn_ref = ipn_data.get('vnp_TxnRef')
    logger.info(f"Nhận được IPN callback từ VNPay cho TxnRef: {vnp_txn_ref}. Data: {ipn_data}")

    # Gọi hàm crud để xử lý (hàm này đã có kiểm tra hash và cập nhật DB)
    success = await crud.handle_vnpay_return(ipn_data)

    # Phản hồi cho VNPAY theo yêu cầu
    if success:
        logger.info(f"Xử lý IPN thành công cho TxnRef: {vnp_txn_ref}")
        return {"RspCode": "00", "Message": "Confirm Success"}
    else:
        # Nếu crud.handle_vnpay_return trả về False (lỗi hash, lỗi DB, hoặc giao dịch không hợp lệ)
        # Vẫn cần trả về lỗi cho VNPAY biết để họ có thể thử gửi lại IPN
        logger.error(f"Xử lý IPN thất bại cho TxnRef: {vnp_txn_ref}")
        # Mã lỗi '99' hoặc mã lỗi cụ thể hơn nếu có thể xác định
        # Quan trọng: KHÔNG trả về 00 nếu xử lý phía bạn lỗi, VNPAY sẽ gửi lại IPN
        return {"RspCode": "99", "Message": "Unknown error"}
# === [HẾT ENDPOINT IPN] ===

# === [SỬA ĐỔI HOÀN TOÀN ENDPOINT NÀY] ===
@app.get("/v1/payment/vnpay_return", tags=["VNPay Callback"])
async def handle_vnpay_return_message(request: Request):
    """
    Endpoint xử lý khi trình duyệt của người dùng được VNPAY chuyển hướng về.
    Chỉ dùng để kiểm tra hash và trả về thông báo JSON (không redirect).
    Logic cập nhật DB chính nằm ở /vnpay_ipn.
    """
    return_data = dict(request.query_params)
    vnp_txn_ref = return_data.get('vnp_TxnRef')
    vnp_response_code = return_data.get('vnp_ResponseCode')
    logger.info(f"Nhận được Return callback từ VNPay cho TxnRef: {vnp_txn_ref}. Code: {vnp_response_code}")

    # --- Bước 1: Vẫn phải kiểm tra Secure Hash ---
    vnp_secure_hash = return_data.pop('vnp_SecureHash', None)
    secret_key = os.getenv("VNP_HASH_SECRET")
    if not secret_key or not vnp_secure_hash:
         logger.error("Thiếu VNP_HASH_SECRET hoặc vnp_SecureHash trong return data.")
         # Trả về lỗi JSON thay vì HTTPException
         return {"RspCode": "97", "Message": "Invalid Data (Missing Hash)"}

    # Sắp xếp lại các tham số còn lại để tạo hash
    input_params = {k: v for k, v in return_data.items() if k.startswith('vnp_')}
    sorted_params = sorted(input_params.items())
    hash_data_string = "&".join([f"{key}={quote_plus(str(value))}" for key, value in sorted_params])
    h = hmac.new(secret_key.encode(), hash_data_string.encode(), hashlib.sha512)
    calculated_hash = h.hexdigest()

    if calculated_hash != vnp_secure_hash:
        logger.error(f"VNPay Return: Sai Secure Hash! TxnRef: {vnp_txn_ref}")
        # Trả về lỗi JSON
        return {"RspCode": "97", "Message": "Invalid Signature"}
    # --- Hết kiểm tra Hash ---

    # --- Bước 2: Trả về thông báo JSON đơn giản ---
    status_message = "Thanh toán thành công (Return URL)" if vnp_response_code == "00" else "Thanh toán thất bại hoặc bị hủy (Return URL)"

    logger.info(f"VNPay Return hợp lệ cho TxnRef: {vnp_txn_ref}. Trạng thái: {status_message}")

    # Trả về JSON để người gọi API (ví dụ: bạn test bằng trình duyệt) thấy
    return {
        "message": status_message,
        "vnp_TxnRef": vnp_txn_ref,
        "vnp_ResponseCode": vnp_response_code
      
    }
# === [HẾT PHẦN SỬA ĐỔI] ===

# --- Root endpoint ---
@app.get("/")
async def root():
    return {"service": "UIT-Go Payment Service", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    try:
        from database import db
        await db.command("ping")
        return {
            "status": "healthy",
            "service": "paymentservice",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service unhealthy")