"""Shared constants used across the classification and risk engine."""

# Keywords used to score free-text classification into a business category
CLASSIFICATION_KEYWORDS = {
    "employee": [
        "employee", "staff", "payroll", "hr", "human resources",
        "salary", "leave", "contract", "employment", "recruitment"
    ],
    "financial": [
        "invoice", "payment", "transaction", "bank", "account",
        "budget", "revenue", "expense", "finance", "accounting"
    ],
    "medical": [
        "medical", "health", "diagnosis", "patient", "treatment",
        "prescription", "doctor", "hospital", "medical aid", "clinic"
    ],
    "legal": [
        "contract", "legal", "lawsuit", "compliance", "regulation",
        "agreement", "litigation", "clause", "liability"
    ],
}

# Weight applied per entity type when computing an aggregate risk score
RISK_WEIGHTS = {
    "SA_ID": 40,
    "SA_PHONE": 15,
    "SA_COMPANY": 10,
    "SA_BANK": 30,
    "SARS": 25,
    "MEDICAL_AID": 30,
    "PERSON": 10,
    "EMAIL_ADDRESS": 10,
    "CREDIT_CARD": 40,
    "LOCATION": 5,
}
