import uuid
from datetime import datetime, timezone 
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from enum import Enum

class DriverStatusEnum(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    ON_TRIP = "ON_TRIP"

class VehicleInfo(BaseModel):
    license_plate: str
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None

class Driver(BaseModel):
    id: str = Field(..., alias="_id") 
    name: str = Field(..., max_length=100)
    phone: str = Field(...) 
    email: Optional[str] = None
    status: DriverStatusEnum = DriverStatusEnum.OFFLINE
    vehicle: Optional[VehicleInfo] = None
    is_active: bool = Field(default=True)
    

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
class DriverWallet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    driver_id: str = Field(...)
    balance: float = Field(default=0.0, ge=0)
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )