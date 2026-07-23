import pytest
from src.detectors.sa_detectors import SAIDValidator


class TestSAIDValidator:
    def test_invalid_length_rejected(self):
        is_valid, error = SAIDValidator.validate("12345")
        assert is_valid is False
        assert "13 digits" in error

    def test_non_numeric_rejected(self):
        is_valid, error = SAIDValidator.validate("abcdefghijklm")
        assert is_valid is False

    def test_extract_info_returns_empty_for_invalid(self):
        info = SAIDValidator.extract_info("123")
        assert info == {}
