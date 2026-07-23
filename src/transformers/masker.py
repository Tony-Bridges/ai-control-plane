"""Standalone masking utilities, split out from Anonymizer for reuse
in contexts that only need masking (not full tokenization)."""
from typing import Dict


def mask_sa_id(value: str) -> str:
    """Show first 3 and last 2 digits of a South African ID number."""
    if len(value) < 6:
        return "*" * len(value)
    return f"{value[:3]}******{value[-2:]}"


def mask_phone(value: str) -> str:
    """Show prefix and last 4 digits of a phone number."""
    if len(value) < 8:
        return f"****{value[-4:]}" if len(value) >= 4 else "*" * len(value)
    if value.startswith("+"):
        return f"{value[:4]}****{value[-4:]}"
    return f"{value[:3]}****{value[-4:]}"


def mask_generic(value: str) -> str:
    """Generic fallback masking for any other entity type."""
    if len(value) > 6:
        return f"{value[:2]}****{value[-2:]}"
    return "*" * len(value)


MASKERS: Dict[str, callable] = {
    "sa_id": mask_sa_id,
    "sa_phone": mask_phone,
}


def mask_value(entity_type: str, value: str) -> str:
    masker = MASKERS.get(entity_type.lower(), mask_generic)
    return masker(value)
