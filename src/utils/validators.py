from typing import List
import logging

logger = logging.getLogger(__name__)


class ValidatorChain:
    """Chain of validators applied to detected entities before they are trusted."""

    def __init__(self):
        self.min_confidence = 0.5

    def validate(self, entity) -> bool:
        """Run all validation checks against a detected entity."""
        if entity is None:
            return False
        if getattr(entity, "confidence", 0) < self.min_confidence:
            return False
        if not getattr(entity, "value", None):
            return False
        return True
