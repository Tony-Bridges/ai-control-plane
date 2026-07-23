import pytest
from src.routing.load_balancer import LoadBalancer
from src.api.models import ModelType


class TestLoadBalancer:
    def test_round_robin_cycles_through_candidates(self):
        lb = LoadBalancer()
        candidates = [ModelType.OPENAI, ModelType.AZURE_OPENAI]
        results = [lb.round_robin("test-key", candidates) for _ in range(4)]
        assert results == [
            ModelType.OPENAI, ModelType.AZURE_OPENAI,
            ModelType.OPENAI, ModelType.AZURE_OPENAI,
        ]

    def test_least_connections_picks_idle_model(self):
        lb = LoadBalancer()
        candidates = [ModelType.OPENAI, ModelType.AZURE_OPENAI]
        active = {ModelType.OPENAI: 5, ModelType.AZURE_OPENAI: 1}
        assert lb.least_connections(candidates, active) == ModelType.AZURE_OPENAI
