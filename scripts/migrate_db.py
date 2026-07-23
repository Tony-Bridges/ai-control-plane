#!/usr/bin/env python
"""Run database migrations for the audit storage schema.

Usage: python scripts/migrate_db.py
"""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.audit.storage import AuditStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    storage = AuditStorage()
    try:
        await storage.initialize()
        logger.info("Migrations applied successfully")
    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
