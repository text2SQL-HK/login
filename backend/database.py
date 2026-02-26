import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

# .env의 개별 접속 정보로 DATABASE_URL 조립
_host = os.getenv("POSTGRE_HOST", "localhost")
_port = os.getenv("POSTGRE_PORT", "5432")
_user = os.getenv("POSTGRE_USER", "postgres")
_pwd = os.getenv("POSTGRE_PWD", "")
_name = os.getenv("POSTGRE_NAME", "login")

DATABASE_URL = f"postgresql+asyncpg://{_user}:{_pwd}@{_host}:{_port}/{_name}"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=20, max_overflow=10)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI 의존성: 요청마다 DB 세션을 생성하고 종료합니다."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
