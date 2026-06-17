import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from core.config import settings

logger = logging.getLogger(__name__)

# Create the high-performance asynchronous engine
# pool_pre_ping checks if the connection is alive before using it, preventing dropped connection errors
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False, # Set to True to debug raw SQL queries
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0
    })

# AsyncSession factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Base class for our ORM models (Marco 2)
Base = declarative_base()

async def get_db_session():
    """
    FastAPI Dependency: Yields a database session per HTTP request or Worker task.
    Ensures that the connection is gracefully closed after usage.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rollback due to error: {e}")
            raise
        finally:
            await session.close()