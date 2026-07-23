from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging
from contextlib import asynccontextmanager

from src.config import settings
from src.utils.database import DatabasePool

logger = logging.getLogger(__name__)

class AuditStorage:
    """Audit storage with multiple backends"""

    def __init__(self):
        self.db = None
        self.clickhouse = None
        self.elasticsearch = None
        self.initialized = False

    async def initialize(self):
        """Initialize storage connections"""
        if self.initialized:
            return

        try:
            # PostgreSQL for hot storage
            self.db = DatabasePool(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD
            )
            await self.db.initialize()

            # ClickHouse for analytics
            # if settings.ENABLE_CLICKHOUSE:
            #     self.clickhouse = ClickHouseClient(...)

            # Elasticsearch for search
            # if settings.ENABLE_ELASTICSEARCH:
            #     self.elasticsearch = ElasticsearchClient(...)

            # Create tables if not exist
            await self._create_tables()

            self.initialized = True
            logger.info("Audit storage initialized")

        except Exception as e:
            logger.error(f"Failed to initialize audit storage: {str(e)}")
            raise

    async def _create_tables(self):
        """Create database tables"""

        # Audit log table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            request_id UUID NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            department VARCHAR(100) NOT NULL,
            action VARCHAR(50) NOT NULL,
            model VARCHAR(50) NOT NULL,
            risk_score INTEGER NOT NULL,
            classification VARCHAR(50) NOT NULL,
            policy_applied VARCHAR(255) NOT NULL,
            pii_detected JSONB NOT NULL,
            prompt_hash VARCHAR(64) NOT NULL,
            response_hash VARCHAR(64),
            ip_address VARCHAR(45),
            user_agent VARCHAR(500),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_department ON audit_logs(department);
        CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
        CREATE INDEX IF NOT EXISTS idx_audit_risk ON audit_logs(risk_score);
        """

        await self.db.execute(create_table_sql)

    async def store_batch(self, entries: List[Dict[str, Any]]):
        """Store batch of audit entries"""
        if not entries:
            return

        try:
            # Prepare batch insert
            insert_sql = """
            INSERT INTO audit_logs (
                id, timestamp, request_id, user_id, department,
                action, model, risk_score, classification,
                policy_applied, pii_detected, prompt_hash,
                response_hash, ip_address, user_agent, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9,
                $10, $11, $12, $13, $14, $15, $16
            )
            """

            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    for entry in entries:
                        await conn.execute(
                            insert_sql,
                            entry["id"],
                            entry["timestamp"],
                            entry["request_id"],
                            entry["user_id"],
                            entry["department"],
                            entry["action"],
                            entry["model"],
                            entry["risk_score"],
                            entry["classification"],
                            entry["policy_applied"],
                            json.dumps(entry["pii_detected"]),
                            entry["prompt_hash"],
                            entry.get("response_hash"),
                            entry.get("ip_address"),
                            entry.get("user_agent"),
                            json.dumps(entry.get("metadata", {}))
                        )

            # Also store in ClickHouse for analytics if enabled
            if self.clickhouse:
                await self._store_clickhouse_batch(entries)

            # Also index in Elasticsearch for search if enabled
            if self.elasticsearch:
                await self._index_elasticsearch_batch(entries)

        except Exception as e:
            logger.error(f"Failed to store audit batch: {str(e)}")
            raise

    async def _store_clickhouse_batch(self, entries: List[Dict[str, Any]]):
        """Store in ClickHouse for analytics"""
        # ClickHouse implementation
        pass

    async def _index_elasticsearch_batch(self, entries: List[Dict[str, Any]]):
        """Index in Elasticsearch for search"""
        # Elasticsearch implementation
        pass

    async def get_audit_by_id(self, audit_id: str) -> Optional[Dict[str, Any]]:
        """Get audit entry by ID"""
        query = "SELECT * FROM audit_logs WHERE id = $1"

        async with self.db.pool.acquire() as conn:
            result = await conn.fetchrow(query, audit_id)
            if result:
                return dict(result)
        return None

    async def search_audits(
        self,
        user_id: Optional[str] = None,
        department: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search audit logs"""

        conditions = []
        params = []
        param_index = 1

        if user_id:
            conditions.append(f"user_id = ${param_index}")
            params.append(user_id)
            param_index += 1

        if department:
            conditions.append(f"department = ${param_index}")
            params.append(department)
            param_index += 1

        if action:
            conditions.append(f"action = ${param_index}")
            params.append(action)
            param_index += 1

        if start_time:
            conditions.append(f"timestamp >= ${param_index}")
            params.append(start_time)
            param_index += 1

        if end_time:
            conditions.append(f"timestamp <= ${param_index}")
            params.append(end_time)
            param_index += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
        SELECT * FROM audit_logs
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT ${param_index}
        """
        params.append(limit)

        async with self.db.pool.acquire() as conn:
            results = await conn.fetch(query, *params)
            return [dict(row) for row in results]

    async def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit statistics"""

        conditions = []
        params = []
        param_index = 1

        if start_time:
            conditions.append(f"timestamp >= ${param_index}")
            params.append(start_time)
            param_index += 1

        if end_time:
            conditions.append(f"timestamp <= ${param_index}")
            params.append(end_time)
            param_index += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        stats_query = f"""
        SELECT
            COUNT(*) as total_requests,
            COUNT(DISTINCT user_id) as unique_users,
            AVG(risk_score) as avg_risk_score,
            MAX(risk_score) as max_risk_score,
            COUNT(CASE WHEN action = 'block' THEN 1 END) as blocked_count,
            COUNT(CASE WHEN action = 'anonymize' THEN 1 END) as anonymized_count,
            COUNT(CASE WHEN action = 'mask' THEN 1 END) as masked_count,
            COUNT(CASE WHEN action = 'allow' THEN 1 END) as allowed_count
        FROM audit_logs
        {where_clause}
        """

        # Department breakdown
        dept_query = f"""
        SELECT
            department,
            COUNT(*) as count,
            AVG(risk_score) as avg_risk
        FROM audit_logs
        {where_clause}
        GROUP BY department
        ORDER BY count DESC
        """

        async with self.db.pool.acquire() as conn:
            stats = await conn.fetchrow(stats_query, *params)
            dept_stats = await conn.fetch(dept_query, *params)

        result = dict(stats)
        result["departments"] = [dict(row) for row in dept_stats]

        return result

    async def close(self):
        """Close storage connections"""
        if self.db:
            await self.db.close()
        if self.clickhouse:
            await self.clickhouse.close()
        if self.elasticsearch:
            await self.elasticsearch.close()
