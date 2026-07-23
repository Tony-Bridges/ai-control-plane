from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from src.api.models import ModelType


@dataclass
class ModelConfig:
    """Runtime configuration for a single upstream model endpoint."""
    model_type: ModelType
    endpoint: str
    api_key: Optional[str]
    timeout: int = 30
    weight: int = 100
    max_tokens: int = 2000
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteDecision:
    """Result of a routing decision, including why the model was chosen."""
    model: ModelType
    reason: str
    fallback_used: bool = False
