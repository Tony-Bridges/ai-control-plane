from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod


@dataclass
class DetectedEntity:
    """Represents a single PII/sensitive entity found in text."""
    entity_type: str
    value: str
    start: int
    end: int
    score: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseDetector(ABC):
    """Base class for all detectors."""

    name: str = "base"

    @abstractmethod
    def detect(self, text: str) -> list:
        """Return a list of DetectedEntity found in text."""
        raise NotImplementedError


class PatternDetector(BaseDetector):
    """Base class for regex-pattern-based detectors (Presidio-style)."""

    def __init__(self, name: str, patterns=None, context=None):
        self.name = name
        self.patterns = patterns or []
        self.context = context or []

    def detect(self, text: str) -> list:
        import re
        entities = []
        for pattern in self.patterns:
            regex = getattr(pattern, "regex", None) or getattr(pattern, "pattern", None)
            if not regex:
                continue
            for match in re.finditer(regex, text):
                entities.append(
                    DetectedEntity(
                        entity_type=self.name,
                        value=match.group(0),
                        start=match.start(),
                        end=match.end(),
                        score=getattr(pattern, "score", 0.5),
                        confidence=getattr(pattern, "score", 0.5),
                    )
                )
        return entities
