from pydantic import BaseModel, Field
from typing import List, Dict, Any

class LocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class NearbyDriver(BaseModel):
    driver_id: str
    distance_km: float
    longitude: float
    latitude: float

class NotificationRequest(BaseModel):
    driver_ids: List[str] = Field(..., description="Danh sách các driver_id cần gửi thông báo")
    payload: Dict[str, Any] = Field(..., description="Nội dung JSON để gửi qua WebSocket")

class SingleNotificationRequest(BaseModel):
    payload: Dict[str, Any] = Field(..., description="Nội dung JSON để gửi qua WebSocket")
