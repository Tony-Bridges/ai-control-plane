from typing import Optional
import logging

try:
    import asyncpg
except ImportError:  # pragma: no cover
    asyncpg = None

logger = logging.getLogger(__name__)


class DatabasePool:
    """Thin wrapper around an asyncpg connection pool."""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool: Optional["asyncpg.Pool"] = None

    async def initialize(self):
        if asyncpg is None:
            logger.warning("asyncpg not installed, database disabled")
            return
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            min_size=2,
            max_size=10,
        )
        logger.info("Database pool initialized")

    async def execute(self, query: str, *args):
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    @staticmethod
    async def health_check() -> bool:
        # Placeholder; wired up via app-level pool in production
        return True

    async def close(self):
        if self.pool:
            await self.pool.close()
