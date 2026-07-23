from typing import List, Dict, Any, Optional
import re
import hashlib
import uuid
import logging
from collections import defaultdict

from src.detectors.sa_detectors import SAIDValidator

logger = logging.getLogger(__name__)

class Anonymizer:
    """Data anonymization and masking engine"""

    def __init__(self):
        self.mask_cache = {}
        self.token_map = {}

    async def anonymize(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> str:
        """Fully anonymize text"""

        # Start with original text
        anonymized = text

        # Process each entity
        for entity in sorted(entities, key=lambda x: x.get("start", 0), reverse=True):
            entity_type = entity.get("entity_type", "")
            value = entity.get("value", "")
            start = entity.get("start", 0)
            end = entity.get("end", 0)

            if not value:
                continue

            # Replace with type-specific token
            replacement = self._generate_token(entity_type, value)

            # Replace in text
            anonymized = anonymized[:start] + replacement + anonymized[end:]

        return anonymized

    async def mask(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> str:
        """Mask sensitive data with partial visibility"""

        masked = text

        for entity in sorted(entities, key=lambda x: x.get("start", 0), reverse=True):
            entity_type = entity.get("entity_type", "")
            value = entity.get("value", "")
            start = entity.get("start", 0)
            end = entity.get("end", 0)

            if not value:
                continue

            replacement = self._mask_entity(value, entity_type)
            masked = masked[:start] + replacement + masked[end:]

        return masked

    async def sanitize_response(
        self,
        response: str,
        entities: List[Dict[str, Any]]
    ) -> str:
        """Sanitize model response"""

        # Check for PII in response
        sanitized = response

        # Re-detect PII in response (simplified)
        # In production, re-run classification on response

        # Remove any potential PII patterns
        patterns = [
            (r'\b[0-9]{13}\b', '[ID_REDACTED]'),  # SA ID
            (r'\b(0[6-8][0-9]|0[1-9][0-9]?)[0-9]{7}\b', '[PHONE_REDACTED]'),  # Phone
            (r'\b[0-9]{4}/[0-9]{6}/[0-9]{2}\b', '[COMPANY_REDACTED]'),  # Company
        ]

        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized)

        return sanitized

    def _generate_token(self, entity_type: str, value: str) -> str:
        """Generate replacement token"""

        # Check cache
        cache_key = f"{entity_type}_{value}"
        if cache_key in self.token_map:
            return self.token_map[cache_key]

        # Generate token based on type
        token_type = entity_type.lower()

        if token_type == "sa_id":
            # Keep some structure but hide details
            token = f"ID-{hashlib.md5(value.encode()).hexdigest()[:8]}"
        elif token_type == "sa_phone":
            token = f"PHONE-{uuid.uuid4().hex[:8]}"
        elif token_type == "sa_company":
            token = f"COMPANY-{hashlib.md5(value.encode()).hexdigest()[:8]}"
        elif token_type == "sa_bank":
            token = f"BANK-{uuid.uuid4().hex[:8]}"
        else:
            token = f"[{token_type.upper()}]"

        # Cache token
        self.token_map[cache_key] = token
        return token

    def _mask_entity(self, value: str, entity_type: str) -> str:
        """Mask entity with partial visibility"""

        entity_type = entity_type.lower()

        if entity_type == "sa_id":
            # Show first 3 and last 2 digits
            return f"{value[:3]}******{value[-2:]}"

        elif entity_type == "sa_phone":
            # Show area code and last 4 digits
            if len(value) >= 10:
                if value.startswith('+'):
                    return f"{value[:4]}****{value[-4:]}"
                else:
                    return f"{value[:3]}****{value[-4:]}"
            return f"****{value[-4:]}"

        elif entity_type == "sa_company":
            # Show year only
            if '/' in value:
                parts = value.split('/')
                if parts:
                    return f"{parts[0]}/******/**"
            return "******"

        elif entity_type == "sa_bank":
            # Show last 4 digits
            return f"****{value[-4:]}"

        else:
            # Generic masking
            if len(value) > 6:
                return f"{value[:2]}****{value[-2:]}"
            else:
                return "*" * len(value)

    def validate_anonymization(self, original: str, anonymized: str) -> bool:
        """Validate that anonymization worked"""
        # Check if any patterns remain
        patterns = [
            r'\b[0-9]{13}\b',
            r'\b(0[6-8][0-9]|0[1-9][0-9]?)[0-9]{7}\b',
            r'\b[0-9]{4}/[0-9]{6}/[0-9]{2}\b'
        ]

        for pattern in patterns:
            if re.search(pattern, anonymized):
                matches = re.findall(pattern, anonymized)
                # Check if matches are from original
                for match in matches:
                    if match in original:
                        return False

        return True
