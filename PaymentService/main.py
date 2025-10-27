from fastapi import FastAPI, HTTPException, status, Request
from typing import List
from urllib.parse import parse_qsl
import os 	
import hashlib 	
import hmac
import crud
import schemas
import models
import httpx

app = FastAPI(
    title="UIT-Go Payment Service",
    description="Microservice để xử lý thanh toán qua ví nội bộ.",
    version="1.1.0"
)

APP_COMMISSION_RATE = 0.20
DRIVER_SERVICE_URL = os.getenv("DRIVER_SERVICE_URL")

@app.get("/users/{user_id}/wallet", response_model=schemas.WalletResponse, tags=["Wallet"])
async def get_user_wallet(user_id: str):
    wallet = await crud.get_or_create_wallet(user_id)
    return wallet

@app.post("/wallets/top-up", response_model=schemas.WalletResponse, tags=["Wallet"])
async def top_up_user_wallet(request: schemas.TopUpRequest):
    updated_wallet = await crud.top_up_wallet(request)
    return updated_wallet

@app.get("/payment-return", tags=["VNPay"])
async def handle_vnpay_return(request: Request):
    input_data = dict(request.query_params)
    
    vnp_secure_hash = input_data.pop('vnp_SecureHash', None)
    
    sorted_params = sorted(input_data.items())
    hash_data_parts = []
    for key, value in sorted_params:
        hash_data_parts.append(f"{key}={str(value)}")
    hash_data_string = "&".join(hash_data_parts)

    secret_key = os.getenv("VNP_HASH_SECRET")
    
    h = hmac.new(secret_key.encode(), hash_data_string.encode(), hashlib.sha512)
    calculated_hash = h.hexdigest()

    if calculated_hash != vnp_secure_hash:
        return {"RspCode": "97", "Message": "Invalid Signature"}

    order_id = input_data.get('vnp_TxnRef')
    response_code = input_data.get('vnp_ResponseCode')
    
    if response_code == "00":
        print(f"Thanh toán THÀNH CÔNG cho đơn hàng {order_id}")

        # Code logic thực tế sẽ được triển khai ở đây
        
        return {"RspCode": "00", "Message": "Confirm Success"}
    else:
        print(f"Thanh toán THẤT BẠI cho đơn hàng {order_id}")
        return {"RspCode": "02", "Message": "Order already confirmed"}
    
    
@app.post("/process-payment", response_model=schemas.PaymentLinkResponse, tags=["Payment"])
async def handle_payment_processing(request: schemas.ProcessPaymentRequest):
    result = await crud.process_payment(request)
    
    if result["status"] == "FAILED":
        raise HTTPException(
            status_code=500,
            detail=result.get("message")
        )
    
    return result
