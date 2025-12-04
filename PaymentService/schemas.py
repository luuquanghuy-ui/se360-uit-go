from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
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

# Trip Completion Payment Schemas
class TripCompletionRequest(BaseModel):
    trip_id: str
    driver_id: str
    user_id: str
    distance_km: float
    payment_method: str  # "BANK_TRANSFER" or "CASH"
    user_bank_info: Optional[Dict[str, Any]] = None  # For bank transfer

class TripFareCalculation(BaseModel):
    distance_km: float
    base_fare: float = Field(default=5000.0)  # 5,000 VND per km
    total_fare: float
    commission_rate: float = Field(default=0.20)  # 20% commission
    commission_amount: float
    driver_earning: float

class MockBankTransferRequest(BaseModel):
    from_account: str
    to_account: str
    amount: float
    description: str

class MockBankTransferResponse(BaseModel):
    success: bool
    transaction_id: str
    message: str
    timestamp: datetime

class TripCompletionResponse(BaseModel):
    success: bool
    trip_id: str
    fare_details: TripFareCalculation
    payment_method: str
    payment_status: str  # "SUCCESS", "FAILED", "PENDING"
    transaction_id: Optional[str] = None
    bank_transfer_result: Optional[MockBankTransferResponse] = None
    driver_wallet_updated: bool = False
    new_driver_balance: Optional[float] = None
    message: Optional[str] = None
