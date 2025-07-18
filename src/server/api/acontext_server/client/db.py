import os
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import event, text
from sqlalchemy.exc import DisconnectionError, OperationalError
from ..schema.orm import Base
from ..env import LOG as logger


class DatabaseClient:
    """
    Best-practice SQLAlchemy database client with connection pooling.

    Features:
    - Async SQLAlchemy with connection pooling
    - Automatic connection recovery
    - Proper session management
    - Connection pool monitoring
    - Health checks
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        logger.info(f"Database URL: {self.database_url}")

        # Convert postgres:// to postgresql+asyncpg:// if needed
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        elif self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace(
                "postgres://", "postgresql+asyncpg://", 1
            )

        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None

    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine, creating it if necessary."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """Get the session maker, creating it if necessary."""
        if self._sessionmaker is None:
            self._sessionmaker = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False,
            )
        return self._sessionmaker

    def _create_engine(self) -> AsyncEngine:
        """Create the SQLAlchemy async engine with optimal settings."""
        engine = create_async_engine(
            self.database_url,
            # Connection pool settings
            poolclass=AsyncAdaptedQueuePool,
            pool_size=50,  # Number of connections to maintain
            max_overflow=50,  # Additional connections beyond pool_size
            pool_timeout=30,  # Seconds to wait for a connection
            pool_recycle=600,  # Recycle connections after 10 minutes
            pool_pre_ping=True,  # Verify connections before use
            # Engine settings
            echo=False,  # Set to True for SQL debugging
            echo_pool=False,  # Set to True for pool debugging
            future=True,  # Use SQLAlchemy 2.0 behavior
            # Connection arguments for asyncpg
            connect_args={
                "server_settings": {
                    "application_name": "acontext_server",
                    "jit": "off",  # Disable JIT for better performance in some cases
                },
                "command_timeout": 60,  # Query timeout in seconds
                "prepared_statement_cache_size": 0,  # Disable prepared statements cache
            },
        )

        # Set up event listeners for connection monitoring
        self._setup_event_listeners(engine)

        return engine

    def _setup_event_listeners(self, engine: AsyncEngine) -> None:
        """Set up event listeners for connection pool monitoring."""

        @event.listens_for(engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            logger.debug("New database connection established")

        @event.listens_for(engine.sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")

        @event.listens_for(engine.sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            logger.debug("Connection returned to pool")

        @event.listens_for(engine.sync_engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            logger.warning(f"Connection invalidated: {exception}")

    async def get_session(self) -> AsyncSession:
        """
        Get a new database session.

        Note: Remember to close the session when done, or use get_session_context().
        """
        return self.sessionmaker()

    @asynccontextmanager
    async def get_session_context(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic cleanup.

        Usage:
            async with db_client.get_session_context() as session:
                # Use session here
                result = await session.execute(select(User))
        """
        session = await self.get_session()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def get_transaction_context(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with explicit transaction management.

        Usage:
            async with db_client.get_transaction_context() as session:
                # All operations in this block are in a transaction
                await session.execute(insert(User).values(name="John"))
                # Transaction is automatically committed unless an exception occurs
        """
        session = await self.get_session()
        async with session.begin():
            try:
                yield session
            except Exception:
                # Transaction will be automatically rolled back
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """
        Perform a health check on the database connection.

        Returns:
            True if the database is accessible, False otherwise.
        """
        try:
            async with self.get_session_context() as session:
                r = await session.execute(text("SELECT 1"))
                return True
        except (DisconnectionError, OperationalError, Exception) as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def create_tables(self) -> None:
        """Create all tables defined in the ORM models."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables defined in the ORM models."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")

    async def close(self) -> None:
        """Close the database engine and all connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
            logger.info("Database connections closed")

    def get_pool_status(self) -> dict:
        """Get current connection pool status for monitoring."""
        if not self._engine:
            return {"status": "engine_not_initialized"}

        pool = self._engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
        }


# Lazy Loading Global database client instance
DB_CLIENT = DatabaseClient()


# Dependency function for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get a database session.

    Usage in FastAPI routes:
        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(User))
            return result.scalars().all()
    """
    async with DB_CLIENT.get_session_context() as session:
        yield session


# Convenience functions
async def init_database() -> None:
    """Initialize the database (create tables)."""
    await DB_CLIENT.create_tables()
    logger.info("Database initialized")


async def close_database() -> None:
    """Close database connections."""
    await DB_CLIENT.close()
    logger.info("Database closed")
