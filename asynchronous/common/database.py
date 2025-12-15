"""
Async database connection and session management.
Shared across all services that use PostgreSQL.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
Base = declarative_base()

# Database configuration from environment variables
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "microservices_db")

# Async PostgreSQL connection string
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class DatabaseManager:
    """
    Manages async database connections and sessions.
    """

    def __init__(self, database_url: str = DATABASE_URL):
        """
        Initialize database engine and session factory.

        Args:
            database_url: SQLAlchemy connection string
        """
        self.engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL query logging
            pool_size=10,  # Connection pool size
            max_overflow=20,  # Extra connections when pool is full
            pool_pre_ping=True,  # Verify connections before use
        )

        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info(f"Database engine created for {DB_HOST}:{DB_PORT}/{DB_NAME}")

    async def create_tables(self) -> None:
        """
        Create all tables defined in Base metadata.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session (async context manager).

        Usage:
            async with db_manager.get_session() as session:
                result = await session.execute(query)
        """
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """
        Close database engine and all connections.
        """
        await self.engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance (initialized per service)
_db_manager: DatabaseManager | None = None


def set_db_manager(db_manager: DatabaseManager) -> None:
    """
    Set the global database manager instance.
    Should be called once during service startup.

    Args:
        db_manager: Initialized DatabaseManager instance
    """
    global _db_manager
    _db_manager = db_manager


# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    Uses the global database manager instance.

    Usage in FastAPI:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    if _db_manager is None:
        raise RuntimeError("Database manager not initialized. Call set_db_manager() during startup.")

    async with _db_manager.get_session() as session:
        yield session
