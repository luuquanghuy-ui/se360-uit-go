# DriverService/main.py
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer 
import crud
import schemas
import models
import auth 
import logging
from typing import Optional, Annotated
import os 
from jose import JWTError, jwt 

app = FastAPI(title="UIT-Go Driver Service")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://userservice:8000/auth/login") 

SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = "HS256" 
SERVICE_AUDIENCE = "driverservice" 
async def verify_service_jwt(token: Annotated[str, Depends(oauth2_scheme)]):
    """Dependency để kiểm tra Service JWT gửi từ service khác."""
    if not SECRET_KEY:
        logger.error("SECRET_KEY chưa được cấu hình phía DriverService!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Secret Key for service validation not configured."
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate service credentials (Invalid Service Token)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=SERVICE_AUDIENCE
        )
        
        token_type: str = payload.get("type")
        if token_type != "service":
             logger.warning(f"Token không hợp lệ, type không phải 'service': {token_type}")
             raise credentials_exception
         
        logger.info(f"Service token hợp lệ từ client: {payload.get('sub')}")

    except JWTError as e:
        logger.error(f"Lỗi xác thực Service JWT: {e}")
        raise credentials_exception

async def get_current_driver(
    token: str = Depends(oauth2_scheme) 
) -> models.Driver: 
    email = await auth.verify_token(token)
    driver = await crud.get_driver_by_email(email=email) 
    
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy tài xế cho token này (hoặc user không phải là DRIVER)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not driver.is_active:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tài khoản tài xế không hoạt động")
         
    return driver

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"service": "UIT-Go Driver Service", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    try:
        from database import database
        if database is not None:
            # Use a simple query instead of ping for CosmosDB compatibility
            await database.get_collection("drivers").find_one({})
            return {
                "status": "healthy",
                "service": "driverservice",
                "database": "connected"
            }
        else:
            raise Exception("Database connection failed")
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.post("/drivers/", response_model=schemas.DriverResponse, status_code=status.HTTP_201_CREATED)
async def create_driver_profile_endpoint(
    user_id: str,
    driver_create: schemas.DriverCreate
):
    driver = await crud.create_driver_profile(driver_create, user_id) 
    if not driver:
        raise HTTPException(status_code=400, detail="Không thể tạo hồ sơ tài xế (có thể đã tồn tại hoặc user_id không hợp lệ)")
    return driver 

@app.get("/drivers/me", response_model=schemas.DriverResponse)
async def get_my_driver_profile(current_driver: models.Driver = Depends(get_current_driver)):
    return current_driver

@app.put("/drivers/me", response_model=schemas.DriverResponse)
async def update_my_driver_profile(
    update_data: schemas.DriverUpdate,
    current_driver: models.Driver = Depends(get_current_driver)
):
    return updated_driver

@app.post("/drivers/me/online", response_model=schemas.DriverResponse)
async def set_driver_status_online(current_driver: models.Driver = Depends(get_current_driver)):
    return updated_driver

@app.post("/drivers/me/offline", response_model=schemas.DriverResponse)
async def set_driver_status_offline(current_driver: models.Driver = Depends(get_current_driver)):
    return updated_driver

@app.post("/drivers/me/update-balance", response_model=schemas.WalletResponse)
async def update_my_balance_endpoint(
    request: schemas.UpdateBalanceRequest,
    current_driver: models.Driver = Depends(get_current_driver) 
):
    return updated_wallet

@app.get("/drivers/me/wallet", response_model=schemas.WalletResponse)
async def get_my_wallet(current_driver: models.Driver = Depends(get_current_driver)):

    return wallet



@app.get(
    "/drivers/internal/{driver_id}", 
    response_model=schemas.DriverResponse,
    dependencies=[Depends(verify_service_jwt)] 
)
async def get_driver_internal(driver_id: str):
    logger.info(f"Yêu cầu nội bộ (JWT hợp lệ): Lấy thông tin cho tài xế {driver_id}")
    
    driver = await crud.get_driver_by_id(driver_id)
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Không tìm thấy tài xế với ID này"
        )
        
    return driver
