from typing import Dict, Any
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricsManager:
    """In-memory metrics collector, exposed via /metrics.

    In production this would be backed by prometheus_client counters/histograms.
    """

    _counters: Dict[str, int] = defaultdict(int)
    _histograms: Dict[str, list] = defaultdict(list)

    @classmethod
    async def initialize(cls):
        logger.info("Metrics manager initialized")

    @classmethod
    async def close(cls):
        logger.info("Metrics manager closed")

    @classmethod
    def record_classification(cls, risk_level, entity_count: int):
        cls._counters[f"classification_risk_{risk_level}"] += 1
        cls._counters["entities_detected_total"] += entity_count

    @classmethod
    def record_policy_decision(cls, action):
        cls._counters[f"policy_decision_{action}"] += 1

    @classmethod
    def record_blocked_request(cls):
        cls._counters["requests_blocked_total"] += 1

    @classmethod
    def record_model_request(cls, model):
        cls._counters[f"model_requests_{model}"] += 1

    @classmethod
    def record_model_error(cls, model, error: str):
        cls._counters[f"model_errors_{model}"] += 1

    @classmethod
    def record_request(cls, processing_time_ms: float, risk_score: int, model):
        cls._histograms["processing_time_ms"].append(processing_time_ms)
        cls._counters["requests_total"] += 1

    @classmethod
    def record_error(cls):
        cls._counters["errors_total"] += 1

    @classmethod
    def get_metrics(cls) -> str:
        """Return metrics in a Prometheus-style plaintext format."""
        lines = []
        for key, value in cls._counters.items():
            lines.append(f"{key} {value}")
        return "\n".join(lines)

    @classmethod
    def get_detailed_metrics(cls) -> Dict[str, Any]:
        return {
            "counters": dict(cls._counters),
            "processing_time_samples": len(cls._histograms.get("processing_time_ms", [])),
        }
