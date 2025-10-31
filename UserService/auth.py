# UserService/auth.py
from datetime import datetime, timedelta, timezone
from typing import Union, Optional 
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from fastapi import HTTPException, status 

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# --- Mã hóa mật khẩu ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # Bcrypt chỉ hỗ trợ tối đa 72 bytes, truncate nếu cần
    import logging
    logger = logging.getLogger(__name__)

    password_bytes = password.encode('utf-8')
    logger.info(f"Password length: {len(password)} chars, {len(password_bytes)} bytes")

    if len(password_bytes) > 72:
        logger.warning(f"Password too long ({len(password_bytes)} bytes), truncating to 72 bytes")
        # Truncate an toàn
        password_bytes = password_bytes[:72]
        # Decode lại, bỏ qua ký tự bị cắt không hợp lệ
        password = password_bytes.decode('utf-8', errors='ignore')
        logger.info(f"Truncated password: {len(password)} chars")

    return pwd_context.hash(password)

# --- Tạo JWT ---
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Xác thực JWT ---
async def verify_token(token: str) -> Optional[str]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception
    
  

def create_service_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Tạo một Access Token (JWT) dành riêng cho giao tiếp giữa các service.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15) 
        
    to_encode.update({"exp": expire})
    to_encode.update({"type": "service"}) 
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt