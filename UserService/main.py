# UserService/main.py 
import os
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter 
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import timedelta
from typing import List, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession 
import logging
import crud
import models
import schemas
import auth
from database import init_db, get_db, Base 


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("UserService: Đang khởi động...")
    try:
        await init_db()
        logger.info("UserService: Khởi động hoàn tất.")
        yield # Ứng dụng chạy ở đây
    finally:
        logger.info("UserService: Đang tắt...")
        # (Không cần đóng engine SQLAlchemy rõ ràng ở đây)
        logger.info("UserService: Tắt hoàn tất.")

# --- KHỞI TẠO FASTAPI APP VỚI LIFESPAN ---
app = FastAPI(
    title="UIT-Go User Service (PostgreSQL)", # <-- Đổi tên
    version="1.0.0",
    lifespan=lifespan
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# --- DEPENDENCIES ---
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    # Inject session vào dependency 
    db: AsyncSession = Depends(get_db)
) -> models.User: # <-- Vẫn trả về Pydantic User model
    email = await auth.verify_token(token)
    # THAY THẾ: Truyền db session vào hàm crud
    user = await crud.get_user_by_email(db=db, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy người dùng cho token này",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# --- ROUTERS ---
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
users_router = APIRouter(prefix="/users", tags=["Users"])

# THÊM: Đọc Client Credentials từ biến môi trường
EXPECTED_TRIPSVC_CLIENT_ID = os.getenv("TRIPSVC_CLIENT_ID")
EXPECTED_TRIPSVC_CLIENT_SECRET = os.getenv("TRIPSVC_CLIENT_SECRET")

# --- ENDPOINTS XÁC THỰC ---

@auth_router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: schemas.UserCreate,
    # THAY THẾ: Đổi từ collection sang db session
    db: AsyncSession = Depends(get_db)
):
    # Dùng hàm crud mới, truyền db
    logger.info(f"UserService: Nhận yêu cầu đăng ký cho email: {user_in.email}")
    try:
        created_user = await crud.create_user(db=db, user_data=user_in)
        # Hàm crud trả về Pydantic User, FastAPI tự serialize
        logger.info(f"UserService: Tạo user thành công: {created_user.email}")
        return created_user
    except ValueError as e:
         # Lỗi ValueError sẽ là lỗi unique constraint (email, phone) hoặc email đã đăng ký
         logger.warning(f"UserService: Validation error khi đăng ký: {str(e)}")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
         logger.error(f"UserService: Lỗi khi tạo user: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lỗi server khi đăng ký.")


@auth_router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user = await crud.get_user_by_email(db=db, email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, # Dùng email làm subject cho user token
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.post("/token", response_model=schemas.Token)
async def login_for_service_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    client_id = form_data.username
    client_secret = form_data.password
    if (client_id == EXPECTED_TRIPSVC_CLIENT_ID and
            client_secret == EXPECTED_TRIPSVC_CLIENT_SECRET):

        # Tạo payload cho service token
        service_token_data = {
            "sub": client_id, 
            "aud": "driverservice" 

        }
        # Gọi hàm tạo service token trong auth.py
        service_token = auth.create_service_access_token(data=service_token_data)

        logger.info(f"Đã cấp Service Token cho client: {client_id}")
        return {"access_token": service_token, "token_type": "bearer"}
    else:
        # Nếu không khớp, từ chối
        logger.warning(f"Client Credentials không hợp lệ: {client_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client Credentials không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

@auth_router.post("/logout")
async def logout(current_user: models.User = Depends(get_current_user)):
     return {"message": f"Người dùng {current_user.email} đã đăng xuất."}


# --- ENDPOINTS QUẢN LÝ USER ---

@users_router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@users_router.put("/me", response_model=schemas.UserResponse)
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.id:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User ID không hợp lệ.")
    try:
        updated_user = await crud.update_user(db=db, user_id=current_user.id, user_update_data=user_update)
    except ValueError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
         logger.error(f"UserService: Lỗi khi cập nhật user {current_user.id}: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lỗi server khi cập nhật.")

    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng để cập nhật.")
    return updated_user

@users_router.get("/email/{email}", response_model=schemas.UserResponse)
async def get_user_by_email_endpoint(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Yêu cầu nội bộ: Lấy thông tin cho email {email}")
    user = await crud.get_user_by_email_internal(db=db, email=email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng với email này"
        )
    return user


# --- INCLUDE ROUTERS VÀ ROOT ENDPOINT ---
app.include_router(auth_router)
app.include_router(users_router)

@app.get("/")
async def root():
    return {"service": "UIT-Go User Service (PostgreSQL)", "status": "running"}