from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Body
from typing import List, Dict
import crud
import schemas
import logging
import json


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="UIT-Go Location Service (Redis + WebSocket)", version="1.0.0")

@app.get("/")
async def root():
    return {"service": "UIT-Go Location Service", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    try:
        import crud
        # Test Redis connection
        result = await crud.redis_client.ping()
        return {
            "status": "healthy",
            "service": "locationservice",
            "database": "connected" if result else "disconnected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

class TripConnectionManager:
    def __init__(self):
        self.active_rooms: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, trip_id: str, user_type: str):
        await websocket.accept()
        if trip_id not in self.active_rooms:
            self.active_rooms[trip_id] = {}
        self.active_rooms[trip_id][user_type] = websocket
        logger.info(f"Phòng {trip_id}: {user_type} đã kết nối.")

    def disconnect(self, trip_id: str, user_type: str):
        if trip_id in self.active_rooms and user_type in self.active_rooms[trip_id]:
            del self.active_rooms[trip_id][user_type]
            if not self.active_rooms[trip_id]: 
                del self.active_rooms[trip_id]
        logger.info(f"Phòng {trip_id}: {user_type} đã ngắt kết nối.")

    async def broadcast_to_passenger(self, trip_id: str, message: dict):
        if trip_id in self.active_rooms:
            passenger_ws = self.active_rooms[trip_id].get("passenger")
            if passenger_ws:
                await passenger_ws.send_json(message)

    async def broadcast_to_driver(self, trip_id: str, message: dict):
        if trip_id in self.active_rooms:
            driver_ws = self.active_rooms[trip_id].get("driver")
            if driver_ws:
                await driver_ws.send_json(message)

trip_manager = TripConnectionManager()





class DriverConnectionManager:
    def __init__(self):
        self.active_drivers: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, driver_id: str):
        await websocket.accept()
        self.active_drivers[driver_id] = websocket
        logger.info(f"Tài xế RẢNH {driver_id} đã kết nối WSS.")

    def disconnect(self, driver_id: str):
        if driver_id in self.active_drivers:
            del self.active_drivers[driver_id]
            logger.info(f"Tài xế RẢNH {driver_id} đã ngắt kết nối WSS.")

    async def send_notification(self, driver_id: str, payload: dict):
        websocket = self.active_drivers.get(driver_id)
        if websocket:
            try:
                await websocket.send_json(payload)
                logger.info(f"Đã gửi thông báo cho tài xế {driver_id}: {payload.get('type')}")
                return True
            except Exception as e:
                logger.warning(f"Lỗi khi gửi thông báo cho {driver_id}: {e}")
                self.disconnect(driver_id) 
        return False

driver_manager = DriverConnectionManager()



@app.websocket("/ws/trip/{trip_id}/{user_type}")
async def ws_trip_tracking(websocket: WebSocket, trip_id: str, user_type: str):
    if user_type not in ["driver", "passenger"]:
        logger.warning(f"Kết nối thất bại: user_type không hợp lệ '{user_type}'")
        return

    await trip_manager.connect(websocket, trip_id, user_type)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            try:
                location = schemas.LocationUpdate(**data)
            except Exception:
                logger.warning(f"Phòng {trip_id}: Dữ liệu vị trí sai định dạng: {data}")
                continue

            if user_type == "driver":
                await trip_manager.broadcast_to_passenger(trip_id, location.model_dump())
            
            elif user_type == "passenger":
                await trip_manager.broadcast_to_driver(trip_id, location.model_dump())

    except WebSocketDisconnect:
        trip_manager.disconnect(trip_id, user_type)
    except Exception as e:
        logger.error(f"Lỗi WebSocket chuyến đi {trip_id} ({user_type}): {e}")
        trip_manager.disconnect(trip_id, user_type)



@app.websocket("/ws/driver/{driver_id}/location")
async def ws_driver_location(websocket: WebSocket, driver_id: str):
    await driver_manager.connect(websocket, driver_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            try:
                location = schemas.LocationUpdate(**data)
                logger.info(f"Tài xế {driver_id} gửi vị trí: lat={location.latitude}, lng={location.longitude}")
                await crud.update_driver_location(
                    driver_id,
                    location.longitude,
                    location.latitude
                )
                logger.info(f"Đã lưu vị trí tài xế {driver_id} vào Redis")
            except Exception as e:
                logger.warning(f"Tài xế {driver_id}: Dữ liệu nhận được không phải định dạng Vị trí: {data}, lỗi: {e}")
                continue
            
    except WebSocketDisconnect:
        logger.info(f"Tài xế {driver_id} (matching) ngắt kết nối WSS.")
        driver_manager.disconnect(driver_id) 
        await crud.remove_driver_location(driver_id) 
    except Exception as e:
        logger.error(f"Lỗi WebSocket tài xế {driver_id}: {e}")
        driver_manager.disconnect(driver_id) 
        await crud.remove_driver_location(driver_id) 


@app.get("/drivers/nearby", response_model=List[schemas.NearbyDriver])
async def get_nearby_drivers(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: int = Query(5, ge=1, le=20),
    limit: int = Query(10, ge=1, le=50)
):
    logger.info(f"Tìm kiếm tài xế gần ({latitude}, {longitude})")
    drivers = await crud.get_nearby_drivers(longitude, latitude, radius_km, limit)
    
    if not drivers:
        logger.warning("Không tìm thấy tài xế nào gần đó.")
        raise HTTPException(status_code=404, detail="Không tìm thấy tài xế nào gần đó.")
    
    return drivers

@app.post("/update")
async def update_location(location: schemas.LocationUpdate):
    await crud.update_driver_location(location.driver_id, location.longitude, location.latitude)
    logger.info(f"Tài xế {location.driver_id} gửi vị trí: lat={location.latitude}, lng={location.longitude}")
    return {"message": "Vị trí đã được cập nhật thành công", "driver_id": location.driver_id}

@app.delete("/driver/{driver_id}/location")
async def set_driver_offline(driver_id: str):
    await crud.remove_driver_location(driver_id)

    driver_manager.disconnect(driver_id)
    logger.info(f"Tài xế {driver_id} đã offline (gọi qua API).")
    return {"message": f"Tài xế {driver_id} đã được xóa khỏi Redis và WSS."}


@app.post("/notify/drivers")
async def notify_drivers_endpoint(request: schemas.NotificationRequest = Body(...)):
    if not request.driver_ids:
        logger.warning("NotifyDrivers: Nhận được yêu cầu nhưng không có driver_ids.")
        return {"message": "Không có tài xế nào để thông báo."}

    sent_count = 0
    failed_ids = []

    logger.info(f"NotifyDrivers: Bắt đầu gửi thông báo '{request.payload.get('type')}' đến {len(request.driver_ids)} tài xế.")
    for driver_id in list(request.driver_ids):
        success = await driver_manager.send_notification(driver_id, request.payload)
        if success:
            sent_count += 1
        else:
            failed_ids.append(driver_id)

    logger.info(f"NotifyDrivers: Gửi thành công {sent_count}/{len(request.driver_ids)}. Thất bại: {failed_ids}")
    return {
        "message": f"Đã gửi thông báo cho {sent_count} tài xế.",
        "sent_count": sent_count,
        "failed_driver_ids": failed_ids
    }
@app.post("/notify/trip/{trip_id}/{user_type}")
async def notify_trip_participant(
    trip_id: str,
    user_type: str,
    request: schemas.SingleNotificationRequest = Body(...)
):
    if user_type == "passenger":
        await trip_manager.broadcast_to_passenger(trip_id, request.payload)
        logger.info(f"NotifyTrip: Đã gửi thông báo cho passenger trong phòng {trip_id}")
        return {"message": f"Đã gửi thông báo cho passenger trong phòng {trip_id}"}
    elif user_type == "driver":
        await trip_manager.broadcast_to_driver(trip_id, request.payload)
        logger.info(f"NotifyTrip: Đã gửi thông báo cho driver trong phòng {trip_id}")
        return {"message": f"Đã gửi thông báo cho driver trong phòng {trip_id}"}
    else:
        raise HTTPException(status_code=400, detail="user_type phải là 'driver' hoặc 'passenger'")
