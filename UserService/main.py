# UserService/main.py

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import timedelta
from typing import List, AsyncGenerator
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorCollection
import logging
import os
import crud
import models
import schemas
import auth 

from database import get_users_collection, create_indexes, get_db_client, _client as db_client


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("UserService: Đang khởi động...")
    try:
        await get_db_client() 
        await create_indexes() 
        logger.info("UserService: Khởi động hoàn tất.")
        yield 
    finally:
        logger.info("UserService: Đang tắt...")
        if db_client: 
             logger.info("UserService: Đã đóng kết nối MongoDB (nếu có).")
        logger.info("UserService: Tắt hoàn tất.")


app = FastAPI(
    title="UIT-Go User Service (MongoDB)",
    version="1.0.0",
    lifespan=lifespan
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")



async def get_collection() -> AsyncIOMotorCollection:
    collection = await get_users_collection()
    if collection is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Không thể kết nối database")
    return collection

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    collection: "motor.motor_asyncio.AsyncIOMotorCollection" = Depends(get_collection)
) -> models.User:
    email = await auth.verify_token(token)
    user = await crud.get_user_by_email(email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy người dùng cho token này",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
users_router = APIRouter(prefix="/users", tags=["Users"])
EXPECTED_TRIPSVC_CLIENT_ID = os.getenv("TRIPSVC_CLIENT_ID")
EXPECTED_TRIPSVC_CLIENT_SECRET = os.getenv("TRIPSVC_CLIENT_SECRET")


@auth_router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: schemas.UserCreate,
    collection: AsyncIOMotorCollection = Depends(get_collection)
):
    existing_user = await crud.get_user_by_email(email=user_in.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email này đã được đăng ký.")
    try:
        created_user = await crud.create_user(user_data=user_in)
        return created_user
    except ValueError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
         logger.error(f"UserService: Lỗi khi tạo user: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lỗi server khi đăng ký.")


@auth_router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    collection: AsyncIOMotorCollection = Depends(get_collection)
):
    user = await crud.get_user_by_email(email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.post("/logout")
async def logout(current_user: models.User = Depends(get_current_user)):
     return {"message": f"Người dùng {current_user.email} đã đăng xuất."}
 




@auth_router.post("/token", response_model=schemas.Token)
async def login_for_service_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    
    client_id = form_data.username
    client_secret = form_data.password

    if (client_id == EXPECTED_TRIPSVC_CLIENT_ID and
            client_secret == EXPECTED_TRIPSVC_CLIENT_SECRET):
        service_token_data = {"sub": client_id} 
        service_token = auth.create_service_access_token(data=service_token_data) 
        
        logger.info(f"Đã cấp Service Token cho client: {client_id}")
        return {"access_token": service_token, "token_type": "bearer"}
    else:
        logger.warning(f"Client Credentials không hợp lệ: {client_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client Credentials không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"}, 
        )



@users_router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@users_router.put("/me", response_model=schemas.UserResponse)
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    collection: "motor.motor_asyncio.AsyncIOMotorCollection" = Depends(get_collection)
):
    if not current_user.id:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User ID không hợp lệ.")

    updated_user = await crud.update_user(user_id=current_user.id, user_update_data=user_update)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không thể cập nhật thông tin người dùng.")
    return updated_user

@users_router.get("/email/{email}", response_model=schemas.UserResponse)
async def get_user_by_email_endpoint(
    email: str,
    collection: AsyncIOMotorCollection = Depends(get_collection)
):
    logger.info(f"Yêu cầu nội bộ: Lấy thông tin cho email {email}")
    user = await crud.get_user_by_email(email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Không tìm thấy người dùng với email này"
        )
    return user

app.include_router(auth_router)
app.include_router(users_router)

@app.get("/")
async def root():
    return {"service": "UIT-Go User Service (MongoDB)", "status": "running"}



