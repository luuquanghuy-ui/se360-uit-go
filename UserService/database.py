import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import AsyncGenerator
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


SQLALCHEMY_DATABASE_URL = os.getenv(
    "SQLALCHEMY_DATABASE_URL", 
    "postgresql+asyncpg://admin:secret@localhost:5432/mydb" 
)


Base = declarative_base()


engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=False, 
    future=True
)


AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False 
)

async def init_db():
    """Khởi tạo và tạo các bảng (tables) nếu chúng chưa tồn tại."""
    logger.info("UserService: Đang khởi tạo bảng PostgreSQL...")
    try:
        import models 
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all) 
        logger.info("UserService: Đã khởi tạo và tạo các bảng PostgreSQL thành công.")
    except Exception as e:
        logger.error(f"UserService: LỖI khi khởi tạo database PostgreSQL: {e}")
        raise

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency Injector: Cung cấp database session cho mỗi endpoint."""
    async with AsyncSessionLocal() as session:
        yield session
