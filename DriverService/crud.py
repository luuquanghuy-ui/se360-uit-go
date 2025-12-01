# DriverService/crud.py

import os
import httpx
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from bson import ObjectId
import logging
import models
import schemas
from database import drivers_collection, driver_wallets_collection
from motor.motor_asyncio import AsyncIOMotorCollection

LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL", "http://locationservice:8000")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://userservice:8000")

#Helper

def driver_helper(driver_data: dict) -> models.Driver:
    if "_id" in driver_data:
        driver_data["id"] = str(driver_data.pop("_id"))
    return models.Driver(**driver_data)

def wallet_helper(wallet_data: dict) -> models.DriverWallet:
    if "_id" in wallet_data:
        wallet_data["id"] = str(wallet_data.pop("_id"))
    return models.DriverWallet(**wallet_data)

async def create_driver_profile(driver_create: schemas.DriverCreate, user_id_str: str) -> Optional[models.Driver]:
    logger = logging.getLogger(__name__)
    if drivers_collection is None:
        logger.error("Lỗi: drivers_collection chưa được khởi tạo.")
        return None
    try:
        driver_oid = ObjectId(user_id_str)
    except Exception:
        logger.warning(f"DriverService: Invalid user_id format: {user_id_str}")
        return None
    existing = await drivers_collection.find_one({"_id": driver_oid})
    if existing:
        logger.info(f"DriverService: Hồ sơ cho {user_id_str} đã tồn tại.")
        return driver_helper(existing)
    try:
        if hasattr(driver_create.vehicle, 'model_dump'):
             vehicle_data = driver_create.vehicle.model_dump()
        elif isinstance(driver_create.vehicle, dict):
             vehicle_data = driver_create.vehicle
        else:
             logger.error(f"Dữ liệu vehicle không hợp lệ: {driver_create.vehicle}")
             raise TypeError("Dữ liệu vehicle không phải dict hoặc Pydantic model")

        vehicle_data.setdefault("license_plate", "Chưa cập nhật")
        vehicle_data.setdefault("seat_type", 4)
        vehicle_info_obj = models.VehicleInfo(**vehicle_data)
        driver_obj = models.Driver(
            id=user_id_str, 
            name=driver_create.name,
            phone=driver_create.phone,
            email=driver_create.email,
            vehicle=vehicle_info_obj, 
            status=models.DriverStatusEnum.OFFLINE
        )
    except (TypeError, ValueError, Exception) as e:
        logger.error(f"Lỗi khi xử lý dữ liệu đầu vào để tạo Driver: {e}", exc_info=True)
        return None
    try:
        driver_doc = driver_obj.model_dump(by_alias=True, exclude={"id"}, exclude_none=True)
        driver_doc["_id"] = driver_oid 

        await drivers_collection.insert_one(driver_doc)

        new_doc = await drivers_collection.find_one({"_id": driver_oid})
        if new_doc:
            return driver_helper(new_doc)
        else:
            logger.error(f"Không thể tìm thấy tài xế vừa tạo với ID: {driver_oid}")
            return None
    except Exception as e:
        logger.error(f"Lỗi khi lưu tài xế vào database: {e}", exc_info=True)
        return None
    
async def get_driver_by_id(driver_id_str: str) -> Optional[models.Driver]:
    if drivers_collection is None: return None
    try:
        driver_oid = ObjectId(driver_id_str)
    except Exception:
        print(f"DriverService: Invalid user_id format: {driver_id_str}")
        return None
    
    driver_data = await drivers_collection.find_one({"_id": driver_oid})
    if driver_data:
        return driver_helper(driver_data)
    return None

async def update_driver_profile(driver_id_str: str, update_data: schemas.DriverUpdate) -> Optional[models.Driver]:
    if drivers_collection is None: return None
    try:
        driver_oid = ObjectId(driver_id_str)
    except Exception:
        return None 
    update_fields = update_data.model_dump(exclude_unset=True)
    if "status" in update_fields:
        del update_fields["status"]
    if not update_fields:
        return await get_driver_by_id(driver_id_str)
    update_fields["updated_at"] = datetime.now(timezone.utc)
    
    result = await drivers_collection.update_one(
        {"_id": driver_oid},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        return None 
    return await get_driver_by_id(driver_id_str)

async def update_driver_status(driver_id_str: str, new_status: str) -> Optional[models.Driver]:
    if drivers_collection is None:
        print("Lỗi: drivers_collection chưa được khởi tạo.")
        return None
    try:
        driver_oid = ObjectId(driver_id_str)
    except Exception:
        print(f"DriverService: Invalid user_id format: {driver_id_str}")
        return None
    try:
        status_enum = models.DriverStatusEnum(new_status)
    except ValueError:
        print(f"Lỗi: Trạng thái '{new_status}' không hợp lệ.")
        return None

    update_result = await drivers_collection.update_one(
        {"_id": driver_oid},
        {
            "$set": {
                "status": status_enum.value,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    if update_result.matched_count > 0:
        updated_driver = await get_driver_by_id(driver_id_str)
        return updated_driver 
    print(f"Không tìm thấy tài xế với ID {driver_id_str} để cập nhật trạng thái.")
    return None


async def get_user_data_from_email(email: str) -> Optional[Dict[str, Any]]:
    url = f"{USER_SERVICE_URL}/users/email/{email}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        print(f"DriverService: Không tìm thấy user bên UserService (lỗi {e.response.status_code})")
        return None
    except httpx.RequestError as e:
        print(f"DriverService: Không thể kết nối UserService: {e}")
        return None

async def get_driver_by_email(email: str) -> Optional[models.Driver]:
    user_data = await get_user_data_from_email(email)
    if not user_data or user_data.get("user_type") != "DRIVER":
        return None 
    
    user_id_str = user_data.get("id") 
    if not user_id_str:
        return None
        
    driver_profile = await get_driver_by_id(user_id_str)
    return driver_profile



async def get_or_create_driver_wallet(driver_id: str) -> Optional[models.DriverWallet]:
    if driver_wallets_collection is None:
        print("Lỗi: driver_wallets_collection chưa được khởi tạo.")
        return None
        
    wallet_data = await driver_wallets_collection.find_one({"driver_id": driver_id})
    if not wallet_data:
        new_wallet = models.DriverWallet(driver_id=driver_id)
        insert_data = new_wallet.model_dump(by_alias=True, exclude_none=True) 
        await driver_wallets_collection.insert_one(insert_data)
        wallet_data = await driver_wallets_collection.find_one({"driver_id": driver_id})
    
    if wallet_data:
        return wallet_helper(wallet_data)
    return None

async def update_driver_balance(driver_id: str, request: schemas.UpdateBalanceRequest) -> Optional[models.DriverWallet]:
    if driver_wallets_collection is None:
        print("Lỗi: driver_wallets_collection chưa được khởi tạo.")
        return None
    wallet = await get_or_create_driver_wallet(driver_id)
    if not wallet:
        return None
        
    await driver_wallets_collection.update_one(
        {"driver_id": driver_id},
        {
            "$inc": {"balance": request.amount},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    
    updated_wallet_data = await driver_wallets_collection.find_one({"driver_id": driver_id})
    if updated_wallet_data:
        return wallet_helper(updated_wallet_data)
    return None



async def get_user_id_by_email(email: str) -> Optional[str]:
    """Lấy user_id từ UserService bằng email."""
    try:
        url = f"{USER_SERVICE_URL}/users/email/{email}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get("id")
            return None
    except Exception as e:
        print(f"Lỗi khi gọi UserService lấy user_id: {e}")
        return None


async def notify_location_service_offline(driver_id: str):
    url = f"{LOCATION_SERVICE_URL}/driver/{driver_id}/location"
    print(f"DriverService: Báo offline cho tài xế {driver_id} tới {url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(url)
            response.raise_for_status()
            print(f"DriverService: Đã báo LocationService xóa {driver_id} khỏi Redis thành công.")
    except httpx.HTTPStatusError as e:
        print(f"DriverService: Lỗi khi báo offline cho LocationService (HTTP {e.response.status_code}): {e.response.text}")
    except httpx.RequestError as e:
        print(f"DriverService: Không thể kết nối đến LocationService để báo offline: {e}")
    except Exception as e:
        print(f"DriverService: Lỗi không xác định khi báo offline: {e}")