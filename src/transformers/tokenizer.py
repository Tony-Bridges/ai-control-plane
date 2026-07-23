"""Reversible tokenization utilities for entities that need to be restored
after model processing (e.g. round-tripping through an external LLM)."""
from typing import Dict, Tuple
import uuid


class ReversibleTokenizer:
    """Maps sensitive values to opaque tokens and back."""

    def __init__(self):
        self._value_to_token: Dict[str, str] = {}
        self._token_to_value: Dict[str, str] = {}

    def tokenize(self, entity_type: str, value: str) -> str:
        if value in self._value_to_token:
            return self._value_to_token[value]

        token = f"__{entity_type.upper()}_{uuid.uuid4().hex[:8]}__"
        self._value_to_token[value] = token
        self._token_to_value[token] = value
        return token

    def detokenize(self, text: str) -> str:
        for token, value in self._token_to_value.items():
            text = text.replace(token, value)
        return text

    def clear(self):
        self._value_to_token.clear()
        self._token_to_value.clear()
