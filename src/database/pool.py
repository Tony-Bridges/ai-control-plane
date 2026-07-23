# src/database/pool.py
import asyncpg
from typing import Optional
import logging
from src.core.config import Settings

logger = logging.getLogger(__name__)

class DatabasePool:
    """Database connection pool manager"""
    
    _instance = None
    _pool = None
    
    def __init__(self):
        # Get settings from config
        settings = Settings()
        self.host = settings.DB_HOST
        self.port = settings.DB_PORT
        self.database = settings.DB_NAME
        self.user = settings.DB_USER
        self.password = settings.DB_PASSWORD
        
        logger.info(f"Database config: host={self.host}, db={self.database}")
    
    async def get_pool(self):
        """Get or create connection pool"""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    min_size=1,
                    max_size=10,
                    command_timeout=60
                )
                logger.info(f"Database pool created for {self.database}")
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise
        return self._pool
    
    async def close(self):
        """Close the connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database pool closed")
            