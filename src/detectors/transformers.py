"""Optional transformer-based (NER model) detectors.

This module is a placeholder hook for swapping in a transformer NER pipeline
(e.g. HuggingFace `dslim/bert-base-NER`) alongside the regex-based SA
detectors, for higher-recall entity detection on unstructured text.
"""
from typing import List
import logging

from src.detectors.base import DetectedEntity

logger = logging.getLogger(__name__)


class TransformerNERDetector:
    """Wraps a HuggingFace token-classification pipeline for NER-based detection."""

    def __init__(self, model_name: str = "dslim/bert-base-NER"):
        self.model_name = model_name
        self._pipeline = None

    def _load(self):
        if self._pipeline is not None:
            return
        try:
            from transformers import pipeline
            self._pipeline = pipeline("ner", model=self.model_name, aggregation_strategy="simple")
        except Exception as e:  # pragma: no cover
            logger.warning(f"Could not load transformer NER model: {e}")
            self._pipeline = None

    def detect(self, text: str) -> List[DetectedEntity]:
        self._load()
        if not self._pipeline:
            return []

        results = self._pipeline(text)
        entities = []
        for r in results:
            entities.append(
                DetectedEntity(
                    entity_type=r.get("entity_group", "UNKNOWN"),
                    value=r.get("word", ""),
                    start=r.get("start", 0),
                    end=r.get("end", 0),
                    score=r.get("score", 0.0),
                    confidence=r.get("score", 0.0),
                )
            )
        return entities
