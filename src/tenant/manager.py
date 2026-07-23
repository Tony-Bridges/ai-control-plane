from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime
import uuid

from src.utils.database import DatabasePool
from src.utils.cache import CacheManager

logger = logging.getLogger(__name__)

class TenantManager:
    """Multi-tenant isolation manager"""
    
    def __init__(self):
        self.db = None
        self.cache = CacheManager()
        
    async def initialize(self):
        """Initialize tenant manager"""
        self.db = DatabasePool()
        await self.db.initialize()
        await self._create_tables()
    
    async def _create_tables(self):
        """Create tenant tables"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS tenants (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            config JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            metadata JSONB
        );
        
        CREATE TABLE IF NOT EXISTS tenant_policies (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(50) NOT NULL,
            policy_id VARCHAR(50) NOT NULL,
            policy_data JSONB NOT NULL,
            version VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_tenant_policies ON tenant_policies(tenant_id, is_active);
        """
        
        await self.db.execute(create_sql)
    
    async def create_tenant(
        self,
        name: str,
        config: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new tenant"""
        tenant_id = str(uuid.uuid4())[:8]
        
        insert_sql = """
        INSERT INTO tenants (id, name, config, metadata)
        VALUES ($1, $2, $3, $4)
        """
        
        await self.db.execute(
            insert_sql,
            tenant_id,
            name,
            json.dumps(config),
            json.dumps(metadata or {})
        )
        
        # Create default tenant policies
        await self._create_default_policies(tenant_id)
        
        # Clear cache
        await self.cache.delete(f"tenant:{tenant_id}")
        
        return tenant_id
    
    async def _create_default_policies(self, tenant_id: str):
        """Create default policies for tenant"""
        default_policies = [
            {
                "policy_id": "default_block",
                "policy_data": {
                    "rules": [
                        {
                            "id": "high_risk_block",
                            "condition": "risk_score > 70",
                            "action": "BLOCK"
                        }
                    ]
                },
                "version": "1.0.0"
            },
            {
                "policy_id": "default_allow",
                "policy_data": {
                    "rules": [
                        {
                            "id": "low_risk_allow",
                            "condition": "risk_score <= 30",
                            "action": "ALLOW"
                        }
                    ]
                },
                "version": "1.0.0"
            }
        ]
        
        for policy in default_policies:
            insert_sql = """
            INSERT INTO tenant_policies (tenant_id, policy_id, policy_data, version)
            VALUES ($1, $2, $3, $4)
            """
            
            await self.db.execute(
                insert_sql,
                tenant_id,
                policy["policy_id"],
                json.dumps(policy["policy_data"]),
                policy["version"]
            )
    
    async def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant configuration"""
        # Check cache
        cache_key = f"tenant:{tenant_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        query = "SELECT * FROM tenants WHERE id = $1 AND is_active = TRUE"
        result = await self.db.fetchone(query, tenant_id)
        
        if result:
            tenant = dict(result)
            tenant["config"] = json.loads(tenant["config"])
            tenant["metadata"] = json.loads(tenant["metadata"]) if tenant["metadata"] else {}
            
            # Cache for 5 minutes
            await self.cache.set(cache_key, tenant, ttl=300)
            
            return tenant
        
        return None
    
    async def get_tenant_policies(
        self,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Get policies for tenant"""
        query = """
        SELECT policy_id, policy_data, version 
        FROM tenant_policies 
        WHERE tenant_id = $1 AND is_active = TRUE
        """
        
        results = await self.db.fetch(query, tenant_id)
        return [
            {
                "policy_id": row["policy_id"],
                "policy_data": json.loads(row["policy_data"]),
                "version": row["version"]
            }
            for row in results
        ]
    
    async def update_tenant_policy(
        self,
        tenant_id: str,
        policy_id: str,
        policy_data: Dict[str, Any],
        version: str
    ) -> bool:
        """Update tenant policy"""
        # Deactivate old policy
        deactivate_sql = """
        UPDATE tenant_policies 
        SET is_active = FALSE 
        WHERE tenant_id = $1 AND policy_id = $2
        """
        await self.db.execute(deactivate_sql, tenant_id, policy_id)
        
        # Insert new policy
        insert_sql = """
        INSERT INTO tenant_policies (tenant_id, policy_id, policy_data, version)
        VALUES ($1, $2, $3, $4)
        """
        
        await self.db.execute(
            insert_sql,
            tenant_id,
            policy_id,
            json.dumps(policy_data),
            version
        )
        
        # Clear cache
        await self.cache.delete(f"tenant_policies:{tenant_id}")
        
        return True
    
    async def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant statistics"""
        stats = {
            "tenant_id": tenant_id,
            "total_requests": 0,
            "requests_by_model": {},
            "requests_by_action": {},
            "average_risk_score": 0,
            "blocked_requests": 0,
            "anonymized_requests": 0,
            "last_activity": None
        }
        
        # Get stats from audit logs
        query = """
        SELECT 
            COUNT(*) as total,
            AVG(risk_score) as avg_risk,
            COUNT(CASE WHEN action = 'block' THEN 1 END) as blocked,
            COUNT(CASE WHEN action = 'anonymize' THEN 1 END) as anonymized
        FROM audit_logs 
        WHERE tenant_id = $1
        """
        
        result = await self.db.fetchone(query, tenant_id)
        if result:
            stats["total_requests"] = result["total"]
            stats["average_risk_score"] = float(result["avg_risk"] or 0)
            stats["blocked_requests"] = result["blocked"]
            stats["anonymized_requests"] = result["anonymized"]
        
        return stats