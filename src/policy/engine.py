from typing import Dict, Any, Optional, List
import json
import logging
import hashlib
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from src.policy.opa_client import OpaClient
from src.policy.version_manager import PolicyVersionManager
from src.api.models import ClassificationResult, ActionType, ModelType
from src.utils.cache import CacheManager
from src.utils.metrics import MetricsManager

logger = logging.getLogger(__name__)

@dataclass
class PolicyResult:
    action: ActionType
    model: Optional[ModelType] = None
    policy_applied: str = ""
    policy_version: str = ""
    reason: str = ""
    audit_level: str = "standard"
    metadata: Dict[str, Any] = field(default_factory=dict)
    compliance_checks: List[str] = field(default_factory=list)

class PolicyEngine:
    """Enhanced policy engine with versioning and multi-tenancy"""
    
    def __init__(self):
        self.opa_client = OpaClient()
        self.version_manager = PolicyVersionManager()
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    async def evaluate(
        self,
        request_data: Dict[str, Any],
        classification: ClassificationResult,
        tenant_id: Optional[str] = None
    ) -> PolicyResult:
        """Evaluate policies with versioning"""
        
        # Get current policy version
        current_version = await self.version_manager.get_current_version()
        
        # Build cache key with tenant and version
        cache_key = f"{tenant_id}_{current_version}_{classification.classification}_{classification.risk_score}_{request_data.get('department')}"
        
        # Check cache
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if (datetime.utcnow() - timestamp).seconds < self.cache_ttl:
                return cached_result
        
        # Build enhanced policy input
        policy_input = {
            "request": {
                "classification": classification.classification,
                "risk_score": classification.risk_score,
                "contains_pii": classification.contains_pii,
                "contains_sa_id": classification.contains_sa_id,
                "detected_entities": classification.detected_entities,
                "confidence_scores": classification.confidence_scores
            },
            "context": {
                "user_id": request_data.get("user_id"),
                "department": request_data.get("department"),
                "environment": request_data.get("environment", "production"),
                "tenant_id": tenant_id or request_data.get("tenant_id"),
                "timestamp": datetime.utcnow().isoformat(),
                "region": request_data.get("region", "global"),
                "purpose": request_data.get("purpose", "general"),
                "model_preference": request_data.get("model_preference"),
                "cost_constraint": request_data.get("cost_constraint"),
                "max_latency_ms": request_data.get("max_latency_ms"),
                "compliance_approved": request_data.get("compliance_approved", False)
            },
            "policy": {
                "version": current_version,
                "effective_date": await self.version_manager.get_effective_date(current_version)
            }
        }
        
        try:
            # Evaluate with OPA
            result = await self.opa_client.evaluate(policy_input)
            
            # Parse OPA result
            action_str = result.get("action", "block")
            model_str = result.get("model")
            policy_applied = result.get("policy_applied", "default")
            policy_version = result.get("policy_version", current_version)
            reason = result.get("reason", "Policy evaluation")
            audit_level = result.get("audit_level", "standard")
            compliance_checks = result.get("compliance_checks", [])
            
            action = ActionType(action_str.lower())
            model = ModelType(model_str) if model_str else None
            
            # Record policy usage
            MetricsManager.record_policy_decision(
                policy_applied, 
                policy_version,
                action
            )
            
            policy_result = PolicyResult(
                action=action,
                model=model,
                policy_applied=policy_applied,
                policy_version=policy_version,
                reason=reason,
                audit_level=audit_level,
                metadata=result.get("metadata", {}),
                compliance_checks=compliance_checks
            )
            
            # Cache result
            self.cache[cache_key] = (policy_result, datetime.utcnow())
            
            # Audit policy evaluation
            await self._audit_policy_evaluation(
                policy_input,
                policy_result
            )
            
            return policy_result
            
        except Exception as e:
            logger.error(f"Policy evaluation failed: {str(e)}")
            MetricsManager.record_policy_error()
            
            # Fail closed - block on error
            return PolicyResult(
                action=ActionType.BLOCK,
                policy_applied="error_fallback",
                policy_version=current_version,
                reason=f"Policy evaluation error: {str(e)}",
                audit_level="full"
            )
    
    async def evaluate_batch(
        self,
        requests: List[Dict[str, Any]],
        classifications: List[ClassificationResult]
    ) -> List[PolicyResult]:
        """Batch evaluate multiple requests"""
        import asyncio
        
        tasks = []
        for i, request_data in enumerate(requests):
            tasks.append(
                self.evaluate(
                    request_data,
                    classifications[i],
                    request_data.get("tenant_id")
                )
            )
        
        return await asyncio.gather(*tasks)
    
    async def _audit_policy_evaluation(
        self,
        policy_input: Dict[str, Any],
        policy_result: PolicyResult
    ):
        """Audit policy evaluation for compliance"""
        # Log policy decision
        logger.info(
            f"Policy decision: {policy_result.action} - "
            f"Version: {policy_result.policy_version} - "
            f"Policy: {policy_result.policy_applied} - "
            f"Reason: {policy_result.reason}"
        )
        
        # Store for audit
        if policy_result.audit_level in ["full", "summary"]:
            # Store in audit system
            from src.audit.logger import AuditLogger
            await AuditLogger.log_policy_evaluation(
                policy_input=policy_input,
                policy_result=policy_result
            )
    
    async def create_policy(
        self,
        policy_data: Dict[str, Any],
        version: Optional[str] = None
    ) -> bool:
        """Create new policy with versioning"""
        try:
            # Generate version if not provided
            if not version:
                version = await self.version_manager.generate_version()
            
            # Add version metadata
            policy_data["version"] = version
            policy_data["created_at"] = datetime.utcnow().isoformat()
            
            # Create in OPA
            success = await self.opa_client.create_policy(policy_data)
            
            if success:
                # Update version manager
                await self.version_manager.add_version(version, policy_data)
                
                # Clear cache
                self.clear_cache()
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to create policy: {str(e)}")
            return False
    
    async def rollback_policy(self, version: str) -> bool:
        """Rollback to previous policy version"""
        try:
            # Get policy for version
            policy_data = await self.version_manager.get_policy(version)
            if not policy_data:
                return False
            
            # Activate version
            success = await self.version_manager.activate_version(version)
            
            if success:
                # Clear cache
                self.clear_cache()
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to rollback policy: {str(e)}")
            return False
    
    def clear_cache(self):
        """Clear policy cache"""
        self.cache.clear()