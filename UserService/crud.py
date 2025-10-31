from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import JSONB, insert
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import ValidationError
import httpx 
import os 
import logging
import json 

from models import User, UserTable, UserTypeEnum 
from schemas import UserCreate, UserUpdate
from auth import get_password_hash

logger = logging.getLogger(__name__)
DRIVER_SERVICE_URL = os.getenv("DRIVER_SERVICE_URL", "http://driverservice:8000")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://userservice:8000") #

# === HÀM HELPER: CHUYỂN ĐỔI JSONB ===

def _prepare_user_data(user_data: UserCreate | UserUpdate) -> Dict[str, Any]:
    """Chuyển đổi các trường lồng (embedded) thành JSON strings/dicts cho SQL."""
    # Logic chuyển đổi Pydantic Models sang dạng lưu trữ trong UserTable
    data = user_data.model_dump(exclude_unset=True)
    
    # Chuẩn bị vehicles (List[VehicleInfo]) và driver_profile (DriverProfileInfo)
    if 'vehicles' in data:
        # Nếu vehicles là list, nó sẽ được lưu thẳng vào cột JSONB
        data['vehicles_json'] = data.pop('vehicles')
    if 'driver_profile' in data:
        # Chuyển driver_profile thành dict để lưu vào JSONB
        data['driver_profile_json'] = data.pop('driver_profile')
        
    return data

# === HÀM READ (ĐỌC) ===

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Lấy người dùng theo email."""
    # SQLAlchemy: SELECT * FROM users WHERE email = :email
    query = select(UserTable).where(UserTable.email == email)
    result = await db.execute(query)
    # scalar_one_or_none trả về object đầu tiên hoặc None
    user_row = result.scalar_one_or_none()
    
    if user_row:
        # User.model_validate(user_row) ánh xạ các cột SQL (id, username, email...)
        # sang User Pydantic Model. from_attributes=True trong models.py làm việc này.
        return User.model_validate(user_row)
    return None

async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Lấy người dùng theo ID."""
    # SQLAlchemy: SELECT * FROM users WHERE id = :user_id
    query = select(UserTable).where(UserTable.id == user_id)
    result = await db.execute(query)
    user_row = result.scalar_one_or_none()
    
    if user_row:
        return User.model_validate(user_row)
    return None

# === HÀM CREATE (TẠO) ===

async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    existing_user = await get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise ValueError("Email đã được đăng ký")

    # Hash password trước khi tạo dict
    hashed_password = get_password_hash(user_data.password)

    # Tạo dict từ user_data, loại bỏ password gốc
    user_data_dict = user_data.model_dump(exclude={"password"}, exclude_none=True)
    # Thêm hashed password vào dict
    user_data_dict["password"] = hashed_password

    db_user = UserTable(**user_data_dict) 
    
    
    try:
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user) 
        
    except Exception as e:
        await db.rollback()
        if 'duplicate key value violates unique constraint' in str(e):
             raise ValueError("Số điện thoại này đã được đăng ký.")
        logger.error(f"PostgreSQL: Lỗi khi tạo user: {e}", exc_info=True)
        raise Exception("Không thể tạo user do lỗi database.")

    created_user = User.model_validate(db_user)
    
    if created_user.user_type == UserTypeEnum.DRIVER:

        await call_create_driver_profile(
            user_id=created_user.id,
            full_name=created_user.full_name,
            phone=created_user.phone, 
            email=created_user.email
        )
        
    return created_user


async def update_user(db: AsyncSession, user_id: str, user_update_data: UserUpdate) -> Optional[User]:
    """Cập nhật thông tin người dùng."""
    user_query = select(UserTable).where(UserTable.id == user_id)
    result = await db.execute(user_query)
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        return None
    
    update_data = user_update_data.model_dump(exclude_unset=True, exclude_none=True)
    
    update_data['updated_at'] = datetime.now(timezone.utc)
    
    stmt = update(UserTable).where(UserTable.id == user_id).values(**update_data)
    
    try:
        await db.execute(stmt)
        await db.commit()
        await db.refresh(db_user)
        return User.model_validate(db_user)
        
    except Exception as e:
        await db.rollback()
        if 'duplicate key value violates unique constraint' in str(e):
             raise ValueError("Số điện thoại này đã được đăng ký bởi người dùng khác.")
        logger.error(f"PostgreSQL: Lỗi khi cập nhật user {user_id}: {e}", exc_info=True)
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

async def get_user_by_email_internal(db: AsyncSession, email: str) -> Optional[User]:
    return await get_user_by_email(db, email)
