from datetime import datetime, date
from typing import Tuple, Optional, Dict, Any
import re
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

class SAIDValidator:
    """Enhanced South African ID Number Validator"""
    
    # Cache for performance
    _cache = {}
    _cache_size = 10000
    
    @classmethod
    def validate(cls, id_number: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate South African ID number
        Returns: (is_valid, error_message, extracted_info)
        """
        # Clean input
        id_number = re.sub(r'[\s\-\.]', '', id_number)
        
        # Check cache
        cache_key = id_number
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        # Basic format checks
        if len(id_number) != 13:
            result = (False, "ID number must be 13 digits", None)
            cls._cache[cache_key] = result
            return result
        
        if not id_number.isdigit():
            result = (False, "ID number must contain only digits", None)
            cls._cache[cache_key] = result
            return result
        
        # Parse components
        try:
            year_str = id_number[0:2]
            month_str = id_number[2:4]
            day_str = id_number[4:6]
            gender_digits = int(id_number[6:10])
            citizenship = int(id_number[10])
            check_digit = int(id_number[12])
        except ValueError:
            result = (False, "Invalid ID number format", None)
            cls._cache[cache_key] = result
            return result
        
        # 1. Validate date (FIXED - uses proper date validation)
        try:
            # Determine century based on current year
            current_year = datetime.now().year
            current_century = (current_year // 100) * 100
            
            # Try both centuries
            birth_date = None
            birth_year = None
            
            for century_offset in [0, -100]:
                year = current_century + century_offset + int(year_str)
                if 1900 <= year <= current_year:
                    try:
                        birth_date = datetime.strptime(
                            f"{year}{month_str}{day_str}", 
                            "%Y%m%d"
                        ).date()
                        birth_year = year
                        break
                    except ValueError:
                        continue
            
            if birth_date is None:
                result = (False, "Invalid date in ID number", None)
                cls._cache[cache_key] = result
                return result
            
            # Check if birth date is not in future
            if birth_date > datetime.now().date():
                result = (False, "Birth date cannot be in future", None)
                cls._cache[cache_key] = result
                return result
            
        except Exception as e:
            result = (False, f"Date validation failed: {str(e)}", None)
            cls._cache[cache_key] = result
            return result
        
        # 2. Validate citizenship digit (FIXED)
        if citizenship not in [0, 1]:
            result = (False, "Invalid citizenship digit (must be 0 or 1)", None)
            cls._cache[cache_key] = result
            return result
        
        # 3. Validate check digit using Luhn (FIXED - more efficient)
        if not cls._luhn_check_fast(id_number):
            result = (False, "Invalid check digit", None)
            cls._cache[cache_key] = result
            return result
        
        # Extract information
        info = cls._extract_info(
            id_number, birth_date, birth_year, 
            gender_digits, citizenship
        )
        
        result = (True, None, info)
        
        # Cache with size limit
        if len(cls._cache) >= cls._cache_size:
            # Remove oldest entry
            cls._cache.pop(next(iter(cls._cache)))
        cls._cache[cache_key] = result
        
        return result
    
    @classmethod
    def _luhn_check_fast(cls, id_number: str) -> bool:
        """Optimized Luhn algorithm for SA ID validation"""
        total = 0
        alt = False
        # Process from right to left (excluding check digit)
        for i in range(11, -1, -1):
            digit = int(id_number[i])
            if alt:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
            alt = not alt
        
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(id_number[12])
    
    @classmethod
    def _extract_info(cls, id_number: str, birth_date: date, 
                     birth_year: int, gender_digits: int, 
                     citizenship: int) -> Dict[str, Any]:
        """Extract detailed information from ID"""
        
        # Determine gender
        gender = "Male" if gender_digits < 5000 else "Female"
        
        # Calculate age
        today = date.today()
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        # Determine citizenship status
        citizenship_status = "SA Citizen" if citizenship == 0 else "Permanent Resident"
        
        return {
            "date_of_birth": birth_date.isoformat(),
            "birth_year": birth_year,
            "age": age,
            "gender": gender,
            "citizenship": citizenship_status,
            "citizenship_code": citizenship,
            "gender_code": gender_digits,
            "is_sa_citizen": citizenship == 0,
            "id_number": cls._mask_id(id_number),
            "century": 2000 if birth_year >= 2000 else 1900
        }
    
    @staticmethod
    def _mask_id(id_number: str) -> str:
        """Mask ID for display"""
        return f"{id_number[:3]}******{id_number[-2:]}"
    
    @classmethod
    def validate_batch(cls, id_numbers: list) -> list:
        """Batch validate ID numbers with parallel processing"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(cls.validate, id_numbers))
        return results
    
    @classmethod
    def clear_cache(cls):
        """Clear validation cache"""
        cls._cache.clear()

# Performance benchmark function
def benchmark_validator():
    """Benchmark validator performance"""
    import time
    import random
    
    # Generate test IDs
    test_ids = []
    for _ in range(10000):
        # Generate random valid-looking ID
        year = random.randint(70, 99)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        gender = random.randint(1000, 9999)
        citizen = random.choice([0, 1])
        base = f"{year:02d}{month:02d}{day:02d}{gender:04d}{citizen}"
        # Calculate check digit
        total = 0
        for i in range(12):
            digit = int(base[i])
            if i % 2 == 0:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        check = (10 - (total % 10)) % 10
        test_ids.append(f"{base}{check}")
    
    # Benchmark
    start = time.time()
    for id_num in test_ids[:1000]:
        SAIDValidator.validate(id_num)
    elapsed = time.time() - start
    
    print(f"Validated 1000 IDs in {elapsed:.3f} seconds")
    print(f"Rate: {1000/elapsed:.1f} IDs/second")
    
    return elapsed