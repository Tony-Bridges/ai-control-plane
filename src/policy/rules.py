"""Static fallback policy rules, used if OPA is unreachable or for local testing."""
from typing import Dict, Any, List
from dataclasses import dataclass, field

from src.api.models import ActionType, ModelType


@dataclass
class StaticRule:
    name: str
    condition: Dict[str, Any]
    action: ActionType
    model: ModelType = ModelType.AZURE_OPENAI
    priority: int = 0


# Default rule set, mirroring config/policies/ai_policy.rego
DEFAULT_RULES: List[StaticRule] = [
    StaticRule(
        name="block_critical_sa_id",
        condition={"contains_sa_id": True, "risk_score_gte": 70},
        action=ActionType.BLOCK,
        priority=100,
    ),
    StaticRule(
        name="anonymize_high_risk",
        condition={"risk_score_gte": 50},
        action=ActionType.ANONYMIZE,
        model=ModelType.AZURE_OPENAI,
        priority=80,
    ),
    StaticRule(
        name="mask_medium_risk",
        condition={"risk_score_gte": 30},
        action=ActionType.MASK,
        model=ModelType.AZURE_OPENAI,
        priority=50,
    ),
    StaticRule(
        name="allow_low_risk",
        condition={"risk_score_gte": 0},
        action=ActionType.ALLOW,
        model=ModelType.OPENAI,
        priority=1,
    ),
]


def evaluate_static_rules(risk_score: int, contains_sa_id: bool) -> StaticRule:
    """Evaluate the static rule set as a fallback to OPA."""
    applicable = [
        r for r in sorted(DEFAULT_RULES, key=lambda x: -x.priority)
        if risk_score >= r.condition.get("risk_score_gte", 0)
        and (not r.condition.get("contains_sa_id") or contains_sa_id)
    ]
    return applicable[0] if applicable else DEFAULT_RULES[-1]
