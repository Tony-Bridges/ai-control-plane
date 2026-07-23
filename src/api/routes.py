from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import requests
import json
import os
import time
import asyncio
from typing import Optional
import logging

from src.api.models import AIRequest, AIResponse, ActionType, ModelType, RiskLevel
from src.detectors.classification_engine import ClassificationEngine
from src.policy.engine import PolicyEngine
from src.routing.router import RoutingEngine
from src.transformers.anonymizer import Anonymizer
from src.audit.logger import AuditLogger
from src.utils.metrics import MetricsManager
from src.utils.cache import CacheManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["ai"])

# Initialize components
classification_engine = ClassificationEngine()
policy_engine = PolicyEngine()
routing_engine = RoutingEngine()
anonymizer = Anonymizer()
audit_logger = AuditLogger()

#============ POLICY MANAGEMENT ENDPOINTS ============

class PolicyCreate(BaseModel):
    name: str
    package: str
    content: str
    enabled: bool = True
    description: Optional[str] = None

class PolicyUpdate(BaseModel):
    content: str
    enabled: bool

@router.get("/policies")
async def list_policies():
    """List all policies"""
    policies = []
    policies_dir = "policies/"
    
    if os.path.exists(policies_dir):
        for filename in os.listdir(policies_dir):
            if filename.endswith(".rego"):
                filepath = os.path.join(policies_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                    policies.append({
                        "id": filename,
                        "name": filename.replace(".rego", ""),
                        "content": content,
                        "created": os.path.getctime(filepath),
                        "updated": os.path.getmtime(filepath)
                    })
    return policies

@router.post("/policies")
async def create_policy(policy: PolicyCreate):
    """Create a new policy"""
    try:
        filename = f"{policy.name}.rego"
        filepath = os.path.join("policies/", filename)
        
        # Add package header if not present
        if not policy.content.startswith(f"package {policy.package}"):
            policy.content = f"package {policy.package}\n\n{policy.content}"
        
        with open(filepath, 'w') as f:
            f.write(policy.content)
        
        # Reload OPA
        requests.post("http://localhost:8181/v1/policies")
        
        return {"status": "success", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/policies/{policy_id}")
async def update_policy(policy_id: str, policy: PolicyUpdate):
    """Update an existing policy"""
    try:
        filepath = os.path.join("policies/", policy_id)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Policy not found")
        
        with open(filepath, 'w') as f:
            f.write(policy.content)
        
        # Reload OPA
        requests.post("http://localhost:8181/v1/policies")
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: str):
    """Delete a policy"""
    try:
        filepath = os.path.join("policies/", policy_id)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Policy not found")
        
        os.remove(filepath)
        
        # Reload OPA
        requests.post("http://localhost:8181/v1/policies")
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/policies/test")
async def test_policy(package: str, rule: str, input_data: Dict[str, Any]):
    """Test a policy rule"""
    try:
        response = requests.post(
            f"http://localhost:8181/v1/data/{package}/{rule}",
            json={"input": input_data}
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/policies/reload")
async def reload_policies():
    """Reload all policies"""
    try:
        response = requests.post("http://localhost:8181/v1/policies")
        return {"status": "policies reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai/process", response_model=AIResponse)
async def process_ai_request(
    request: Request,
    ai_request: AIRequest
) -> AIResponse:
    """Process AI request with full pipeline"""

    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        # 1. Classify request
        classification_result = await classification_engine.classify(
            ai_request.prompt,
            context={
                "user_id": ai_request.user_id,
                "department": ai_request.department
            }
        )

        # Update metrics
        MetricsManager.record_classification(
            classification_result.risk_level,
            len(classification_result.detected_entities)
        )

        logger.info(
            f"Classification complete - Risk: {classification_result.risk_level}, "
            f"Score: {classification_result.risk_score}"
        )

        # 2. Evaluate policy
        policy_result = await policy_engine.evaluate(
            request_data=ai_request.dict(),
            classification=classification_result
        )

        # Update metrics
        MetricsManager.record_policy_decision(policy_result.action)

        logger.info(
            f"Policy decision: {policy_result.action} - "
            f"Policy: {policy_result.policy_applied}"
        )

        # 3. Process based on action
        response_text = None
        model_used = None

        if policy_result.action == ActionType.BLOCK:
            MetricsManager.record_blocked_request()
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Request blocked by security policy",
                    "reason": policy_result.reason,
                    "risk_score": classification_result.risk_score
                }
            )

        elif policy_result.action == ActionType.ANONYMIZE:
            # Transform prompt
            transformed_prompt = await anonymizer.anonymize(
                ai_request.prompt,
                classification_result.detected_entities
            )

            # Route to model
            model_used = await routing_engine.route(
                transformed_prompt,
                classification_result,
                ai_request.model_preference
            )

            # Send to model
            response_text = await routing_engine.send_to_model(
                model_used,
                transformed_prompt,
                ai_request.context
            )

            # Sanitize response
            response_text = await anonymizer.sanitize_response(
                response_text,
                classification_result.detected_entities
            )

        elif policy_result.action == ActionType.MASK:
            # Mask sensitive data
            masked_prompt = await anonymizer.mask(
                ai_request.prompt,
                classification_result.detected_entities
            )

            model_used = await routing_engine.route(
                masked_prompt,
                classification_result,
                ai_request.model_preference
            )

            response_text = await routing_engine.send_to_model(
                model_used,
                masked_prompt,
                ai_request.context
            )

        else:  # ALLOW or AUDIT_ONLY
            # Direct routing
            model_used = await routing_engine.route(
                ai_request.prompt,
                classification_result,
                ai_request.model_preference
            )

            response_text = await routing_engine.send_to_model(
                model_used,
                ai_request.prompt,
                ai_request.context
            )

        # 4. Audit
        audit_id = await audit_logger.log_audit(
            request_id=request_id,
            user_id=ai_request.user_id,
            department=ai_request.department,
            action=policy_result.action,
            model=model_used,
            risk_score=classification_result.risk_score,
            classification=classification_result.classification,
            pii_detected=classification_result.detected_entities,
            policy_applied=policy_result.policy_applied,
            request_data=ai_request.dict(),
            response_data=response_text,
            metadata={
                "ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )

        # 5. Cache response if appropriate
        if classification_result.risk_level == RiskLevel.LOW:
            await CacheManager.cache_response(
                request_id,
                response_text,
                ttl=3600  # 1 hour
            )

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000

        # Update metrics
        MetricsManager.record_request(
            processing_time,
            classification_result.risk_score,
            model_used
        )

        # Return response
        return AIResponse(
            request_id=request_id,
            action=policy_result.action,
            model_used=model_used,
            response=response_text,
            audit_id=audit_id,
            risk_score=classification_result.risk_score,
            classification=classification_result.classification,
            processing_time_ms=processing_time,
            metadata={
                "policy_applied": policy_result.policy_applied,
                "detected_entities": classification_result.detected_entities
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        MetricsManager.record_error()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/cache/{request_id}")
async def get_cached_response(request_id: str):
    """Get cached response"""
    cached = await CacheManager.get_cached_response(request_id)
    if cached:
        return JSONResponse(content={"response": cached})
    raise HTTPException(status_code=404, detail="Response not found")

@router.post("/admin/policies")
async def create_policy(rule: dict):
    """Create new policy rule"""
    # Implementation for policy management
    pass

@router.get("/metrics/detailed")
async def get_detailed_metrics():
    """Get detailed metrics"""
    return MetricsManager.get_detailed_metrics()
