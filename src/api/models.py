from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionType(str, Enum):
    BLOCK = "block"
    ANONYMIZE = "anonymize"
    MASK = "mask"
    ALLOW = "allow"
    AUDIT_ONLY = "audit_only"

class ModelType(str, Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    LOCAL_LLAMA = "local_llama"
    CUSTOM = "custom"

class ClassificationResult(BaseModel):
    classification: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    contains_pii: bool
    contains_sa_id: bool
    detected_entities: List[str]
    confidence_scores: Dict[str, float]
    metadata: Optional[Dict[str, Any]] = None

class AIRequest(BaseModel):
    """AI Request Model"""
    user_id: str = Field(..., description="User identifier")
    department: str = Field(..., description="Department name")
    prompt: str = Field(..., description="User prompt")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    model_preference: Optional[ModelType] = None
    environment: str = Field(default="production")
    session_id: Optional[str] = None

    @validator('department')
    def validate_department(cls, v):
        allowed = ['engineering', 'hr', 'finance', 'medical', 'legal', 'sales']
        if v.lower() not in allowed:
            raise ValueError(f'Department must be one of {allowed}')
        return v.lower()

    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be development, staging, or production')
        return v

class AIResponse(BaseModel):
    """AI Response Model"""
    request_id: str
    action: ActionType
    model_used: ModelType
    response: Optional[str] = None
    audit_id: str
    risk_score: int
    classification: str
    processing_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None

class AuditLog(BaseModel):
    """Audit Log Model"""
    id: str
    timestamp: datetime
    user_id: str
    department: str
    action: ActionType
    model_used: ModelType
    risk_score: int
    classification: str
    prompt_hash: str
    response_hash: Optional[str] = None
    pii_detected: List[str]
    policy_applied: str
    ip_address: str
    user_agent: str
    metadata: Dict[str, Any]

class PolicyRule(BaseModel):
    """Policy Rule Model"""
    id: str
    name: str
    description: str
    department: Optional[str] = None
    classification: Optional[str] = None
    risk_threshold: Optional[int] = None
    action: ActionType
    model_override: Optional[ModelType] = None
    enabled: bool = True
    priority: int = 0
    conditions: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RoutingRule(BaseModel):
    """Routing Rule Model"""
    id: str
    name: str
    condition: Dict[str, Any]
    model: ModelType
    fallback_model: Optional[ModelType] = None
    load_balancing: str = "round_robin"
    weight: int = 100
    enabled: bool = True
    timeout_seconds: int = 30
    retry_count: int = 3

class DetectionResult(BaseModel):
    """Detection Result Model"""
    entities: List[Dict[str, Any]]
    classification: str
    risk_score: int
    risk_level: RiskLevel
    contains_pii: bool
    contains_sa_id: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float
