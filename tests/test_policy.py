import pytest
from src.policy.rules import evaluate_static_rules, DEFAULT_RULES
from src.api.models import ActionType


class TestStaticRules:
    def test_low_risk_allows(self):
        rule = evaluate_static_rules(risk_score=5, contains_sa_id=False)
        assert rule.action == ActionType.ALLOW

    def test_high_risk_anonymizes(self):
        rule = evaluate_static_rules(risk_score=55, contains_sa_id=False)
        assert rule.action == ActionType.ANONYMIZE

    def test_critical_sa_id_blocks(self):
        rule = evaluate_static_rules(risk_score=80, contains_sa_id=True)
        assert rule.action == ActionType.BLOCK
