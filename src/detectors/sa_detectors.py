from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, date
import re
import logging
from presidio_analyzer import PatternRecognizer, Pattern, LocalRecognizer
from presidio_analyzer.context_aware_enhancers import ContextAwareEnhancer

from src.detectors.base import BaseDetector, PatternDetector, DetectedEntity

logger = logging.getLogger(__name__)

class SAIDValidator:
    """South African ID Number Validator with full implementation"""

    @staticmethod
    def validate(id_number: str) -> Tuple[bool, Optional[str]]:
        """Validate South African ID number"""
        # Clean input
        id_number = re.sub(r'[\s\-\.]', '', id_number)

        # Basic checks
        if len(id_number) != 13:
            return False, "ID number must be 13 digits"

        if not id_number.isdigit():
            return False, "ID number must contain only digits"

        # Parse components
        try:
            year = int(id_number[0:2])
            month = int(id_number[2:4])
            day = int(id_number[4:6])
            gender_digits = int(id_number[6:10])
            citizenship = int(id_number[10])
            check_digit = int(id_number[12])
        except ValueError:
            return False, "Invalid ID number format"

        # Validate date
        try:
            # Handle 1900-2099
            full_year = 2000 + year if year < 24 else 1900 + year
            date(full_year, month, day)
        except ValueError:
            return False, "Invalid date in ID number"

        # Validate citizenship
        if citizenship not in [0, 1]:
            return False, "Invalid citizenship digit"

        # Validate check digit using Luhn
        if not SAIDValidator._luhn_check(id_number):
            return False, "Invalid check digit"

        return True, None

    @staticmethod
    def _luhn_check(id_number: str) -> bool:
        """Implement Luhn algorithm for SA ID validation"""
        total = 0
        # Process first 12 digits
        for i in range(12):
            digit = int(id_number[i])
            if i % 2 == 0:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit

        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(id_number[12])

    @staticmethod
    def extract_info(id_number: str) -> Dict[str, Any]:
        """Extract detailed information from SA ID"""
        id_number = re.sub(r'[\s\-\.]', '', id_number)
        if len(id_number) != 13:
            return {}

        year = int(id_number[0:2])
        month = int(id_number[2:4])
        day = int(id_number[4:6])
        gender_digits = int(id_number[6:10])
        citizenship = int(id_number[10])

        # Determine gender
        gender = "Male" if gender_digits < 5000 else "Female"

        # Determine age
        full_year = 2000 + year if year < 24 else 1900 + year
        try:
            birth_date = date(full_year, month, day)
            today = date.today()
            age = today.year - birth_date.year
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1
        except:
            age = None

        # Determine citizenship status
        citizenship_status = "SA Citizen" if citizenship == 0 else "Permanent Resident"

        return {
            "date_of_birth": f"{full_year}-{month:02d}-{day:02d}",
            "age": age,
            "gender": gender,
            "citizenship": citizenship_status,
            "year": full_year,
            "month": month,
            "day": day,
            "citizenship_code": citizenship,
            "gender_code": gender_digits,
            "is_sa_citizen": citizenship == 0
        }

class SAIDDetector(PatternRecognizer):
    """South African ID Number Detector using Presidio"""

    def __init__(self):
        patterns = [
            Pattern(
                "SA ID (13 digits)",
                r"\b([0-9]{2})([0-9]{2})([0-9]{2})([0-9]{4})([0-9]{2})\b",
                0.85
            ),
            Pattern(
                "SA ID (with hyphens)",
                r"\b([0-9]{2})-([0-9]{2})-([0-9]{2})-([0-9]{4})-([0-9]{2})\b",
                0.9
            ),
            Pattern(
                "SA ID (with spaces)",
                r"\b([0-9]{2}) ([0-9]{2}) ([0-9]{2}) ([0-9]{4}) ([0-9]{2})\b",
                0.8
            ),
            Pattern(
                "SA ID (with dots)",
                r"\b([0-9]{2})\.([0-9]{2})\.([0-9]{2})\.([0-9]{4})\.([0-9]{2})\b",
                0.8
            )
        ]

        context = [
            "id number", "identity", "sa id", "south african id",
            "identity number", "id no", "national id", "identity document",
            "id", "passport", "identity card"
        ]

        super().__init__(
            name="SA_ID",
            patterns=patterns,
            context=context,
            supported_language="en",
            supported_entity=["SA_ID"]
            
        )

    def validate_result(self, pattern_result):
        """Validate detected ID using Luhn algorithm"""
        if not pattern_result:
            return None

        # Get the full match
        match = pattern_result.original_match
        if not match:
            return None

        # Extract the ID number
        id_number = re.sub(r'[\s\-\.]', '', match.group(0))
        is_valid, error = SAIDValidator.validate(id_number)

        if is_valid:
            # Extract info for context
            info = SAIDValidator.extract_info(id_number)
            pattern_result.additional_info = info
            pattern_result.score = 0.95
            return pattern_result

        return None

class SAPhoneDetector(PatternRecognizer):
    """South African Phone Number Detector"""

    def __init__(self):
        patterns = [
            Pattern(
                "SA Cell (local)",
                r"\b(0[6-8][0-9]|0[1-9][0-9]?)[0-9]{7}\b",
                0.85
            ),
            Pattern(
                "SA Cell (international)",
                r"\b(\+27|0027)[6-8][0-9]{8}\b",
                0.9
            ),
            Pattern(
                "SA Landline",
                r"\b(0[1-5][0-9]|0[1-9][0-9]?)[0-9]{6,7}\b",
                0.7
            ),
            Pattern(
                "SA Phone with spaces",
                r"\b(\+27|0)[6-8] [0-9]{3} [0-9]{4}\b",
                0.85
            ),
            Pattern(
                "SA Phone with dashes",
                r"\b(\+27|0)[6-8]-[0-9]{3}-[0-9]{4}\b",
                0.85
            )
        ]

        context = [
            "cell", "mobile", "phone", "cellular", "tel", "telephone",
            "contact", "number", "call", "message", "sms", "whatsapp"
        ]

        super().__init__(
            name="SA_PHONE",
            patterns=patterns,
            context=context,
            supported_language="en",
            supported_entity=["SA_ID", "SA_PHONE"]
        )

    def validate_result(self, pattern_result):
        """Validate phone number"""
        if not pattern_result:
            return None

        match = pattern_result.original_match
        if not match:
            return None

        phone = re.sub(r'[\s\-\.]', '', match.group(0))

        # Basic validation
        if len(phone) < 9 or len(phone) > 13:
            return None

        # Check if it's a valid SA prefix
        if phone.startswith('+27') or phone.startswith('0027'):
            if not phone[3:].isdigit():
                return None
        elif not phone.isdigit():
            return None

        pattern_result.score = 0.9
        return pattern_result

class SACompanyDetector(PatternRecognizer):
    """South African Company Registration Detector"""

    def __init__(self):
        patterns = [
            Pattern(
                "SA Company (CIPC format)",
                r"\b([0-9]{4})/([0-9]{6})/([0-9]{2})\b",
                0.85
            ),
            Pattern(
                "SA Company (with spaces)",
                r"\b([0-9]{4}) / ([0-9]{6}) / ([0-9]{2})\b",
                0.8
            ),
            Pattern(
                "SA Company (CK format)",
                r"\bCK[0-9]{4}/[0-9]{6}/[0-9]{2}\b",
                0.9
            ),
            Pattern(
                "SA Company (Close Corp)",
                r"\b[0-9]{4}/[0-9]{6}/[0-9]{2}/[0-9]{2}\b",
                0.8
            )
        ]

        context = [
            "company", "registration", "reg no", "ck", "close corp",
            "enterprise", "business", "pty", "ltd", "corporation",
            "registration number", "company number", "company reg"
        ]

        super().__init__(
            name="SA_COMPANY",
            patterns=patterns,
            context=context,
            supported_language="en",
            supported_entity=["SA_COMPANY"]
        )

    def validate_result(self, pattern_result):
        """Validate company registration"""
        if not pattern_result:
            return None

        match = pattern_result.original_match
        if not match:
            return None

        reg_number = match.group(0)

        # Basic validation
        if len(reg_number) < 10 or len(reg_number) > 20:
            return None

        # Extract year
        year_match = re.search(r'\b([0-9]{4})', reg_number)
        if year_match:
            year = int(year_match.group(1))
            if year < 1900 or year > datetime.now().year:
                return None

        pattern_result.score = 0.85
        return pattern_result

class SABankDetector(PatternRecognizer):
    """South African Bank Account Detector"""

    def __init__(self):
        patterns = [
            Pattern(
                "SA Bank Account",
                r"\b[0-9]{6,10}\b",
                0.6
            ),
            Pattern(
                "SA Bank Account (with branches)",
                r"\b[0-9]{2,4}[-\s][0-9]{6,10}\b",
                0.7
            )
        ]

        context = [
            "bank", "account", "acc no", "account number",
            "banking", "transaction", "transfer", "payment",
            "eft", "bank account", "savings", "cheque", "current account"
        ]

        super().__init__(
            name="SA_BANK",
            patterns=patterns,
            context=context,
            supported_language="en",
            supported_entity=["SA_BANK"]
        )

    def validate_result(self, pattern_result):
        """Validate bank account"""
        if not pattern_result:
            return None

        match = pattern_result.original_match
        if not match:
            return None

        account = re.sub(r'[\s\-]', '', match.group(0))

        # Must be digits and reasonable length
        if not account.isdigit() or len(account) < 6 or len(account) > 10:
            return None

        pattern_result.score = 0.7
        return pattern_result

class SARSDetector(PatternRecognizer):
    """SARS Reference Number Detector"""

    def __init__(self):
        patterns = [
            Pattern(
                "SARS Reference",
                r"\b[0-9]{4}[0-9]{6}[0-9]{3}\b",
                0.8
            ),
            Pattern(
                "SARS IT Number",
                r"\b[0-9]{4}[0-9]{6,7}\b",
                0.7
            ),
            Pattern(
                "SARS Reference with hyphens",
                r"\b[0-9]{4}-[0-9]{6}-[0-9]{3}\b",
                0.85
            )
        ]

        context = [
            "sars", "tax", "reference", "ref no", "tax number",
            "income tax", "vat", "paye", "tax clearance",
            "tax reference", "taxpayer", "tax registration"
        ]

        super().__init__(
            name="SARS",
            patterns=patterns,
            context=context,
            supported_language="en",
            supported_entity=["SARS"]
        )

class MedicalAidDetector(PatternRecognizer):
    """South African Medical Aid Detector"""

    def __init__(self):
        patterns = [
            Pattern(
                "Medical Aid Number",
                r"\b[0-9]{6,10}\b",
                0.6
            ),
            Pattern(
                "Medical Aid with letters",
                r"\b[A-Z][0-9]{5,9}\b",
                0.7
            )
        ]

        context = [
            "medical aid", "medical scheme", "health insurance",
            "member number", "medical plan", "health cover",
            "discovery", "momentum", "medshield", "bonitas",
            "medscheme", "health policy"
        ]

        super().__init__(
            name="MEDICAL_AID",
            patterns=patterns,
            context=context,
            supported_language="en",
            supported_entity=["MEDICAL_AID"]
        )

    def validate_result(self, pattern_result):
        """Validate medical aid number"""
        if not pattern_result:
            return None

        match = pattern_result.original_match
        if not match:
            return None

        # Check length
        aid_number = match.group(0)
        if len(aid_number) < 6 or len(aid_number) > 10:
            return None

        pattern_result.score = 0.75
        return pattern_result
