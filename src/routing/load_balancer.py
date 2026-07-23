from typing import List, Dict
import random
import itertools
import logging

from src.api.models import ModelType

logger = logging.getLogger(__name__)


class LoadBalancer:
    """Simple load balancing strategies across a set of healthy models."""

    def __init__(self):
        self._round_robin_cycles: Dict[str, itertools.cycle] = {}

    def round_robin(self, key: str, candidates: List[ModelType]) -> ModelType:
        if key not in self._round_robin_cycles:
            self._round_robin_cycles[key] = itertools.cycle(candidates)
        return next(self._round_robin_cycles[key])

    def weighted_random(self, candidates: List[ModelType], weights: List[int]) -> ModelType:
        return random.choices(candidates, weights=weights)[0]

    def least_connections(self, candidates: List[ModelType], active_connections: Dict[ModelType, int]) -> ModelType:
        return min(candidates, key=lambda m: active_connections.get(m, 0))
