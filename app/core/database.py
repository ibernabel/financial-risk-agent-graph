"""
Database connection and checkpointing management.

Provides async PostgreSQL connection pooling and LangGraph checkpoint persistence.
"""

import asyncpg
from typing import Optional
from contextlib import asynccontextmanager
from app.core.config import settings


class DatabaseManager:
    """
    Manages PostgreSQL connection pool and provides database operations.

    Uses asyncpg for high-performance async PostgreSQL access.
    """

    def __init__(self) -> None:
        """Initialize database manager."""
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """
        Create connection pool.

        Should be called on application startup.
        """
        if self.pool is not None:
            return

        # Extract connection parameters from URL
        dsn = str(settings.database.url).replace(
            "postgresql+asyncpg://", "postgresql://")

        self.pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=settings.database.pool_size,
            max_size=settings.database.pool_size + settings.database.max_overflow,
            command_timeout=settings.database.pool_timeout,
        )

    async def disconnect(self) -> None:
        """
        Close connection pool.

        Should be called on application shutdown.
        """
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def health_check(self) -> bool:
        """
        Check database connectivity.

        Returns:
            True if database is accessible, False otherwise.
        """
        if self.pool is None:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.

        Usage:
            async with db.transaction() as conn:
                await conn.execute("INSERT INTO ...")
        """
        if self.pool is None:
            raise RuntimeError(
                "Database pool not initialized. Call connect() first.")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    async def initialize_schema(self) -> None:
        """
        Initialize database schema for checkpointing.

        Creates the checkpoints table if it doesn't exist.
        """
        if self.pool is None:
            raise RuntimeError(
                "Database pool not initialized. Call connect() first.")

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    parent_checkpoint_id TEXT,
                    type TEXT,
                    checkpoint JSONB NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id 
                ON checkpoints(thread_id);
                
                CREATE INDEX IF NOT EXISTS idx_checkpoints_created_at 
                ON checkpoints(created_at);
                """
            )

    async def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_ns: str,
        checkpoint_id: str,
        checkpoint_data: dict,
        metadata: Optional[dict] = None,
        parent_checkpoint_id: Optional[str] = None,
    ) -> None:
        """
        Save a checkpoint to the database.

        Args:
            thread_id: Conversation thread identifier
            checkpoint_ns: Checkpoint namespace
            checkpoint_id: Unique checkpoint identifier
            checkpoint_data: Checkpoint state data
            metadata: Optional metadata
            parent_checkpoint_id: Optional parent checkpoint ID
        """
        if self.pool is None:
            raise RuntimeError(
                "Database pool not initialized. Call connect() first.")

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO checkpoints 
                (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, checkpoint, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id)
                DO UPDATE SET 
                    checkpoint = EXCLUDED.checkpoint,
                    metadata = EXCLUDED.metadata,
                    created_at = NOW()
                """,
                thread_id,
                checkpoint_ns,
                checkpoint_id,
                parent_checkpoint_id,
                checkpoint_data,
                metadata or {},
            )

    async def load_checkpoint(
        self, thread_id: str, checkpoint_ns: str, checkpoint_id: Optional[str] = None
    ) -> Optional[dict]:
        """
        Load a checkpoint from the database.

        Args:
            thread_id: Conversation thread identifier
            checkpoint_ns: Checkpoint namespace
            checkpoint_id: Optional specific checkpoint ID (loads latest if None)

        Returns:
            Checkpoint data or None if not found
        """
        if self.pool is None:
            raise RuntimeError(
                "Database pool not initialized. Call connect() first.")

        async with self.pool.acquire() as conn:
            if checkpoint_id:
                row = await conn.fetchrow(
                    """
                    SELECT checkpoint, metadata, created_at
                    FROM checkpoints
                    WHERE thread_id = $1 AND checkpoint_ns = $2 AND checkpoint_id = $3
                    """,
                    thread_id,
                    checkpoint_ns,
                    checkpoint_id,
                )
            else:
                row = await conn.fetchrow(
                    """
                    SELECT checkpoint, metadata, created_at
                    FROM checkpoints
                    WHERE thread_id = $1 AND checkpoint_ns = $2
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    thread_id,
                    checkpoint_ns,
                )

            if row:
                return {
                    "checkpoint": dict(row["checkpoint"]),
                    "metadata": dict(row["metadata"]) if row["metadata"] else {},
                    "created_at": row["created_at"].isoformat(),
                }
            return None


# Global database manager instance
db = DatabaseManager()
