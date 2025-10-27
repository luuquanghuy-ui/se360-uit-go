from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from enum import Enum

class UserTypeEnum(str, Enum):
    PASSENGER = "PASSENGER"
    DRIVER = "DRIVER"

class VehicleInfo(BaseModel):
    vehicle_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    license_plate: str
    seat_type: int
  

class DriverProfileInfo(BaseModel):
    license_num: str
    birth: datetime
    card_num: str
    rating_score: Optional[float] = None

class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    username: str = Field(..., max_length=100)
    email: EmailStr = Field(...)
    password: str = Field(...)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, unique=True)
    user_type: UserTypeEnum
    is_active: bool = Field(default=True)
    email_verified: bool = Field(default=False)
    phone_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    driver_profile: Optional[DriverProfileInfo] = None
    vehicles: List[VehicleInfo] = Field(default_factory=list)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
