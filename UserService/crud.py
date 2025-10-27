# UserService/crud.py

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
from bson import ObjectId 
import uuid
from datetime import datetime, timezone 

from database import get_users_collection
from models import User, UserTypeEnum
from schemas import UserCreate, UserUpdate
from auth import get_password_hash
import httpx  
import os     
import logging

logger = logging.getLogger(__name__)
DRIVER_SERVICE_URL = os.getenv("DRIVER_SERVICE_URL", "http://localhost:8003")

async def get_user_by_email(email: str) -> Optional[User]:
    users_collection = await get_users_collection()
    if users_collection is not None:
        user_data = await users_collection.find_one({"email": email})
        if user_data:
            user_data["id"] = str(user_data.pop("_id", None))
            return User(**user_data)
    return None

async def get_user_by_id(user_id: str) -> Optional[User]:
    users_collection = await get_users_collection()
    if users_collection is not None:
        try:
            query_id = ObjectId(user_id)
            user_data = await users_collection.find_one({"_id": query_id})
            
            if user_data:
                user_data["id"] = str(user_data.pop("_id", None))
                return User(**user_data)
        except Exception as e:
            print(f"Lỗi khi tìm user by ID (có thể ID không hợp lệ): {e}")
            return None
    return None


async def create_user(user_data: UserCreate) -> User:
    users_collection = await get_users_collection()
    if users_collection is None:
        raise Exception("Không thể kết nối collection 'users'")
    existing_user = await users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise ValueError("Email đã được đăng ký")
    hashed_password = get_password_hash(user_data.password)
    user_model_data = user_data.model_dump(exclude={"password"})
    user_model_data["password"] = hashed_password
    new_user = User(**user_model_data)
    user_doc = new_user.model_dump(by_alias=True, exclude={"id"}) 
    if user_doc.get('phone') is None:
        del user_doc['phone']
    result = await users_collection.insert_one(user_doc) 
    created_user_data = await users_collection.find_one({"_id": result.inserted_id})
    
    if created_user_data:
        created_user_data["id"] = str(created_user_data.pop("_id", None))
        created_user = User(**created_user_data)
        if created_user.user_type == UserTypeEnum.DRIVER:
            await call_create_driver_profile(
                user_id=created_user.id,
                full_name=created_user.full_name,
                phone=created_user.phone, 
                email=created_user.email
            )
        return created_user
    else:
        raise Exception("Không thể tạo user")

async def update_user(user_id: str, user_update_data: UserUpdate) -> Optional[User]:
    users_collection = await get_users_collection()
    if users_collection is None: return None
    
    update_fields = user_update_data.model_dump(exclude_unset=True)
    update_fields["updated_at"] = datetime.now(timezone.utc)
    
    try:
        query_id = ObjectId(user_id)
        result = await users_collection.update_one(
            {"_id": query_id}, {"$set": update_fields}
        )
        if result.modified_count == 1:
            updated_user = await get_user_by_id(user_id)
            return updated_user
        elif result.matched_count == 1:
             existing_user = await get_user_by_id(user_id)
             return existing_user
        else:
            return None
    except Exception as e:
        print(f"Lỗi khi cập nhật user (có thể ID không hợp lệ): {e}")
        return None

async def call_create_driver_profile(user_id: str, full_name: Optional[str], phone: Optional[str], email: str):
    if not DRIVER_SERVICE_URL:
        logger.error("DRIVER_SERVICE_URL chưa được cấu hình. Bỏ qua việc tạo hồ sơ tài xế.")
        return
    url = f"{DRIVER_SERVICE_URL}/drivers/?user_id={user_id}"
    driver_payload = {
        "name": full_name or "Tài xế mới",
        "phone": phone or "Chưa cập nhật",
        "email": email,
        "vehicle": {
            "license_plate": "Chưa cập nhật",
            "seat_type": 4
        }
    }
    
    logger.info(f"Đang gọi DriverService để tạo hồ sơ cho user {user_id} tại {url}...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=driver_payload, timeout=10.0)
            
            if response.status_code == 201:
                logger.info(f"Tạo hồ sơ tài xế thành công cho user {user_id}.")
            elif response.status_code == 400:
                logger.warning(f"Hồ sơ tài xế cho user {user_id} có thể đã tồn tại.")
            else:
                response.raise_for_status()
                
    except httpx.RequestError as e:
        logger.error(f"Lỗi khi gọi DriverService (tại {e.request.url!r}): {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"DriverService trả lỗi: {e.response.status_code} - {e.response.text}")
    except Exception as e:
         logger.error(f"Lỗi không xác định khi gọi DriverService: {e}")