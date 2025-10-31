# UserService/auth.py
from datetime import datetime, timedelta, timezone
from typing import Union, Optional 
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from fastapi import HTTPException, status 

SECRET_KEY = os.getenv("SECRET_KEY", "a55d72bab7476385e3114ea4cdd7eff2a7f0bc1bdb690dc4d539f0367c3b3d63")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# --- Mã hóa mật khẩu ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # Bcrypt chỉ hỗ trợ tối đa 72 bytes, truncate nếu cần
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
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