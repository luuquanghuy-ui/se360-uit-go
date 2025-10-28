from sqlalchemy import Column, String, Boolean, DateTime, Float, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB # Dùng JSONB để lưu cấu trúc lồng
from pydantic import BaseModel, EmailStr, Field as PydanticField
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from enum import Enum
from database import Base 

class UserTypeEnum(str, Enum):
    PASSENGER = "PASSENGER"
    DRIVER = "DRIVER"

class VehicleInfo(BaseModel):
    vehicle_id: str = PydanticField(default_factory=lambda: str(uuid.uuid4()))
    license_plate: str
    seat_type: int

class DriverProfileInfo(BaseModel):
    license_num: str
    birth: datetime
    card_num: str
    rating_score: Optional[float] = None


# === 1. SQLAlchemy MODELS (Database Tables) ===

class UserTable(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False) 
    password = Column(String, nullable=False) 
    phone = Column(String, unique=True, nullable=True) 
    full_name = Column(String, nullable=True)
    user_type = Column(SQLEnum(UserTypeEnum), default=UserTypeEnum.PASSENGER, nullable=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    driver_profile_json = Column(JSONB, nullable=True) 
    vehicles_json = Column(JSONB, default=lambda: [], nullable=False) 
class User(BaseModel):
    id: Optional[str] = PydanticField(None) 
    username: str
    email: EmailStr
    password: str 
    full_name: Optional[str] = None
    phone: Optional[str] = None
    user_type: UserTypeEnum
    is_active: bool = True
    email_verified: bool = False
    phone_verified: bool = False
    created_at: datetime
    updated_at: datetime
    driver_profile: Optional[DriverProfileInfo] = PydanticField(None, alias="driver_profile_json")
    vehicles: List[VehicleInfo] = PydanticField([], alias="vehicles_json")

    class Config:
        from_attributes = True 
        populate_by_name = True 
