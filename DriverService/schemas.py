# DriverService/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from models import DriverStatusEnum, VehicleInfo 


class VehicleInfoCreate(BaseModel):
    license_plate: str
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None

class DriverCreate(BaseModel):
    name: str = Field(..., max_length=100)
    phone: str = Field(...) 
    email: Optional[str] = None
    vehicle: Optional[VehicleInfoCreate] = None



class DriverUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = None
    vehicle: Optional[VehicleInfoCreate] = None
    is_active: Optional[bool] = None

class DriverStatusUpdate(BaseModel):
    status: DriverStatusEnum 


class DriverResponse(BaseModel):
    id: str = Field(..., alias="_id") 
    name: str
    phone: str
    email: Optional[str] = None
    status: DriverStatusEnum
    vehicle: Optional[VehicleInfo] = None 
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)


class UpdateBalanceRequest(BaseModel):
    amount: float 
    trip_id: Optional[str] = None
    note: Optional[str] = None

class WalletResponse(BaseModel):
    id: str = Field(..., alias="_id")
    driver_id: str
    balance: float
    updated_at: datetime
    
    model_config = ConfigDict(populate_by_name=True)