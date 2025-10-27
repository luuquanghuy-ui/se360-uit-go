from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
# from models import TransactionStatus # Không cần thiết nếu không dùng trực tiếp ở đây

class TopUpRequest(BaseModel):
    user_id: str
    amount: float = Field(..., gt=0)

class WalletResponse(BaseModel):
    user_id: str
    balance: float
    updated_at: datetime

class ProcessPaymentRequest(BaseModel):
    trip_id: str
    user_id: str
    driver_id: str
    amount: float = Field(..., gt=0)

class PaymentLinkResponse(BaseModel):
    status: str
    payUrl: str
