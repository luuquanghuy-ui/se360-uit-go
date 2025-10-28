from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
import uuid
from models import UserTypeEnum, VehicleInfo, DriverProfileInfo

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None

class UserCreate(BaseModel):
    username: str = Field(..., max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = None
    user_type: UserTypeEnum

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = None

class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    user_type: UserTypeEnum
    is_active: bool
    email_verified: bool
    phone_verified: bool
    created_at: datetime
    updated_at: datetime
    driver_profile: Optional[DriverProfileInfo] = None
    vehicles: List[VehicleInfo] = []

    model_config = ConfigDict(populate_by_name=True)


class DriverProfileUpdate(BaseModel):
    license_num: Optional[str] = None
    birth: Optional[datetime] = None
    card_num: Optional[str] = None
    rating_score: Optional[float] = None



class VehicleCreate(BaseModel):
    license_plate: str
    seat_type: int

class VehicleUpdate(BaseModel):
    license_plate: Optional[str] = None
    seat_type: Optional[int] = None