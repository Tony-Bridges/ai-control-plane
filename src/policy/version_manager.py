from typing import Dict, Any, Optional, List
import json
import hashlib
from datetime import datetime
import logging
import uuid

from src.utils.database import DatabasePool

logger = logging.getLogger(__name__)

class PolicyVersionManager:
    """Manage policy versions with full history"""
    
    def __init__(self):
        self.db = None
        self.cache = {}
        self.current_version = None
        
    async def initialize(self):
        """Initialize the policy version manager"""
        try:
            # Create database pool with environment variables
            self.db = DatabasePool()
            # If your DatabasePool requires initialization:
            # await self.db.initialize()
            logger.info("PolicyVersionManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PolicyVersionManager: {e}")
            raise
    
    async def get_version(self, policy_id: str) -> str:
        """Get current version of a policy"""
        # Placeholder - implement actual logic
        return "1.0.0"
    
    async def create_version(self, policy_id: str, content: str) -> str:
        """Create a new policy version"""
        # Placeholder - implement actual logic
        return "1.0.1"
   
    #async def initialize(self):
    #    """Initialize version manager"""
   #     self.db = DatabasePool()
   #     await self.db.initialize()
        
        # Create tables if not exist
     #   await self._create_tables()
        
        # Load current version
   #     await self._load_current_version()
    
    async def _create_tables(self):
        """Create policy version tables"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS policy_versions (
            version VARCHAR(50) PRIMARY KEY,
            policy_data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255),
            is_active BOOLEAN DEFAULT FALSE,
            checksum VARCHAR(64) NOT NULL,
            metadata JSONB
        );
        
        CREATE INDEX IF NOT EXISTS idx_policy_active ON policy_versions(is_active);
        CREATE INDEX IF NOT EXISTS idx_policy_created ON policy_versions(created_at);
        """
        
        await self.db.execute(create_table_sql)
    
    async def get_current_version(self) -> str:
        """Get current active policy version"""
        if self.current_version:
            return self.current_version
        
        await self._load_current_version()
        return self.current_version or "1.0.0"
    
    async def _load_current_version(self):
        """Load current active version"""
        query = """
        SELECT version FROM policy_versions 
        WHERE is_active = TRUE 
        ORDER BY created_at DESC 
        LIMIT 1
        """
        
        result = await self.db.fetchone(query)
        if result:
            self.current_version = result["version"]
        else:
            # Create initial version
            await self._create_initial_version()
    
    async def _create_initial_version(self):
        """Create initial policy version"""
        initial_policy = {
            "name": "Initial Policy",
            "version": "1.0.0",
            "description": "Initial policy set",
            "rules": [
                {
                    "id": "default_block",
                    "condition": "risk_score > 70",
                    "action": "BLOCK"
                },
                {
                    "id": "default_mask",
                    "condition": "risk_score > 30 AND risk_score <= 70",
                    "action": "MASK"
                },
                {
                    "id": "default_allow",
                    "condition": "risk_score <= 30",
                    "action": "ALLOW"
                }
            ]
        }
        
        await self.add_version("1.0.0", initial_policy, is_active=True)
    
    async def add_version(
        self, 
        version: str, 
        policy_data: Dict[str, Any],
        is_active: bool = False,
        created_by: str = "system"
    ) -> bool:
        """Add new policy version"""
        
        # Calculate checksum
        checksum = hashlib.sha256(
            json.dumps(policy_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Deactivate other versions if this is active
        if is_active:
            await self._deactivate_all_versions()
        
        insert_sql = """
        INSERT INTO policy_versions (
            version, policy_data, created_by, is_active, checksum, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6)
        """
        
        try:
            await self.db.execute(
                insert_sql,
                version,
                json.dumps(policy_data),
                created_by,
                is_active,
                checksum,
                json.dumps({"created_at": datetime.utcnow().isoformat()})
            )
            
            if is_active:
                self.current_version = version
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add policy version: {str(e)}")
            return False
    
    async def get_policy(self, version: str) -> Optional[Dict[str, Any]]:
        """Get policy for specific version"""
        query = "SELECT policy_data FROM policy_versions WHERE version = $1"
        
        result = await self.db.fetchone(query, version)
        if result:
            return json.loads(result["policy_data"])
        return None
    
    async def get_policy_history(
        self, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get policy version history"""
        query = """
        SELECT version, created_at, created_by, is_active, checksum
        FROM policy_versions
        ORDER BY created_at DESC
        LIMIT $1
        """
        
        results = await self.db.fetch(query, limit)
        return [dict(row) for row in results]
    
    async def activate_version(self, version: str) -> bool:
        """Activate a specific version"""
        # Deactivate all versions
        await self._deactivate_all_versions()
        
        # Activate specific version
        update_sql = """
        UPDATE policy_versions 
        SET is_active = TRUE 
        WHERE version = $1
        """
        
        try:
            await self.db.execute(update_sql, version)
            self.current_version = version
            return True
        except Exception as e:
            logger.error(f"Failed to activate version: {str(e)}")
            return False
    
    async def _deactivate_all_versions(self):
        """Deactivate all versions"""
        update_sql = "UPDATE policy_versions SET is_active = FALSE"
        await self.db.execute(update_sql)
    
    async def compare_versions(
        self,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """Compare two policy versions"""
        policy1 = await self.get_policy(version1)
        policy2 = await self.get_policy(version2)
        
        if not policy1 or not policy2:
            return {"error": "Version not found"}
        
        # Calculate differences
        diff = {
            "version1": version1,
            "version2": version2,
            "rules_added": [],
            "rules_removed": [],
            "rules_modified": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Compare rules (simplified)
        rules1 = {r["id"]: r for r in policy1.get("rules", [])}
        rules2 = {r["id"]: r for r in policy2.get("rules", [])}
        
        for rule_id in rules1:
            if rule_id not in rules2:
                diff["rules_removed"].append(rule_id)
            elif rules1[rule_id] != rules2[rule_id]:
                diff["rules_modified"].append(rule_id)
        
        for rule_id in rules2:
            if rule_id not in rules1:
                diff["rules_added"].append(rule_id)
        
        return diff
    
    async def get_effective_date(self, version: str) -> str:
        """Get effective date for version"""
        query = """
        SELECT created_at FROM policy_versions 
        WHERE version = $1
        """
        
        result = await self.db.fetchone(query, version)
        if result:
            return result["created_at"].isoformat()
        return datetime.utcnow().isoformat()
    
    async def generate_version(self) -> str:
        """Generate next version number"""
        query = """
        SELECT version FROM policy_versions 
        ORDER BY created_at DESC 
        LIMIT 1
        """
        
        result = await self.db.fetchone(query)
        if result:
            current = result["version"]
            parts = current.split(".")
            if len(parts) == 3:
                major, minor, patch = parts
                return f"{major}.{minor}.{int(patch) + 1}"
        
        return "1.0.0"