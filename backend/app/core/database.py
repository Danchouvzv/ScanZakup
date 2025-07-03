"""
Database configuration and connection management.

FAANG-grade async PostgreSQL setup with connection pooling and session management.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Create async engine with proper configuration
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,  # Recycle connections every 5 minutes
    pool_size=20,      # Connection pool size
    max_overflow=0,    # No additional connections beyond pool_size
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create all tables."""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they are registered with Base
            from app.models import (  # noqa: F401
                trd_buy,
                lot,
                contract,
                participant,
                raw_data,
            )
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error("❌ Failed to initialize database", error=str(e))
        raise


async def close_db() -> None:
    """Close database connections."""
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error("❌ Error closing database connections", error=str(e))


# Database utilities for testing
class DatabaseManager:
    """Database manager for advanced operations."""
    
    @staticmethod
    async def create_test_db():
        """Create test database."""
        # This would be implemented for test database creation
        pass
    
    @staticmethod
    async def drop_test_db():
        """Drop test database."""
        # This would be implemented for test database cleanup
        pass
    
    @staticmethod
    async def truncate_tables(session: AsyncSession, tables: list = None):
        """Truncate specified tables or all tables."""
        if tables is None:
            tables = Base.metadata.tables.keys()
        
        for table_name in tables:
            await session.execute(f"TRUNCATE TABLE {table_name} CASCADE")
        await session.commit()


# Connection health check
async def check_db_health() -> dict:
    """
    Check database connection health.
    
    Returns:
        dict: Health status information
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute("SELECT 1")
            result.scalar()
            
        return {
            "status": "healthy",
            "database": "connected",
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
        }
        
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        } 