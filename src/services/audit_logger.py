import logging
from datetime import datetime
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)

class AuditLogger:
    """Audit logging service"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def initialize(cls):
        """Initialize the audit logger (class method)"""
        if not cls._initialized:
            instance = cls()
            # Add any initialization logic here
            logger.info("AuditLogger initialized successfully")
            cls._initialized = True
        return cls._instance
    
    async def log_event(self, event_type: str, data: Dict[str, Any], tenant_id: Optional[str] = None):
        """Log an audit event"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data,
            "tenant_id": tenant_id or "default"
        }
        logger.info(f"AUDIT: {json.dumps(log_entry)}")
        # You could also write to a database or file her