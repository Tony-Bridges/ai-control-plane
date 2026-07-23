from typing import Dict, Any, Optional, List
import json
import hashlib
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, asdict

from src.audit.storage import AuditStorage
from src.config import settings

logger = logging.getLogger(__name__)

@dataclass
class AuditEntry:
    """Audit log entry"""
    id: str
    timestamp: datetime
    request_id: str
    user_id: str
    department: str
    action: str
    model: str
    risk_score: int
    classification: str
    policy_applied: str
    pii_detected: List[str]
    prompt_hash: str
    response_hash: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Dict[str, Any]

class AuditLogger:
    """Audit logging system"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.storage = AuditStorage()
            self.initialized = True
            self.buffer = []
            self.buffer_size = 100

    async def initialize(self):
        """Initialize audit system"""
        await self.storage.initialize()
        logger.info("Audit system initialized")

    async def close(self):
        """Close audit system"""
        if self.buffer:
            await self.flush_buffer()
        await self.storage.close()
        logger.info("Audit system closed")

    async def log_audit(
        self,
        request_id: str,
        user_id: str,
        department: str,
        action: str,
        model: str,
        risk_score: int,
        classification: str,
        pii_detected: List[str],
        policy_applied: str,
        request_data: Dict[str, Any],
        response_data: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log an audit entry"""

        audit_id = str(uuid.uuid4())

        # Hash sensitive data
        prompt_hash = hashlib.sha256(
            request_data.get("prompt", "").encode()
        ).hexdigest()

        response_hash = None
        if response_data:
            response_hash = hashlib.sha256(
                response_data.encode()
            ).hexdigest()

        # Create audit entry
        entry = AuditEntry(
            id=audit_id,
            timestamp=datetime.utcnow(),
            request_id=request_id,
            user_id=user_id,
            department=department,
            action=action,
            model=model,
            risk_score=risk_score,
            classification=classification,
            policy_applied=policy_applied,
            pii_detected=pii_detected,
            prompt_hash=prompt_hash,
            response_hash=response_hash,
            ip_address=metadata.get("ip") if metadata else None,
            user_agent=metadata.get("user_agent") if metadata else None,
            metadata=metadata or {}
        )

        # Add to buffer
        self.buffer.append(entry)

        # Flush if buffer is full
        if len(self.buffer) >= self.buffer_size:
            await self.flush_buffer()

        # Also log to structured logger
        logger.info(
            f"AUDIT: {action} - {user_id} - {department} - {classification}",
            extra={
                "audit_id": audit_id,
                "request_id": request_id,
                "action": action,
                "risk_score": risk_score
            }
        )

        return audit_id

    async def flush_buffer(self):
        """Flush audit buffer to storage"""
        if not self.buffer:
            return

        try:
            entries = [asdict(entry) for entry in self.buffer]
            await self.storage.store_batch(entries)
            self.buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush audit buffer: {str(e)}")

    async def get_audit_by_id(self, audit_id: str) -> Optional[Dict[str, Any]]:
        """Get audit entry by ID"""
        return await self.storage.get_audit_by_id(audit_id)

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
        return await self.storage.search_audits(
            user_id=user_id,
            department=department,
            action=action,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

    async def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit statistics"""
        return await self.storage.get_statistics(start_time, end_time)
