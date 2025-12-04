import uuid
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field

class TransactionType(str, Enum):
    PAYMENT = "PAYMENT"
    TOPUP = "TOPUP"
    EARNING ="EARNING"

class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class Wallet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str = Field(..., unique=True)
    balance: float = Field(default=0.0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True

class DriverWallet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    driver_id: str = Field(..., unique=True)
    balance: float = Field(default=0.0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    wallet_id: str = Field(...)
    transaction_type: TransactionType = Field(...)
    amount: float = Field(...)
    trip_id: Optional[str] = None
    status: TransactionStatus = Field(...)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None

    class Config:
        populate_by_name = True