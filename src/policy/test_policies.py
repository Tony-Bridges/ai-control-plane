import requests
import json

# OPA endpoint
OPA_URL = "http://localhost:8181/v1/data"

def test_policy(package, rule, input_data):
    """Test a policy rule"""
    response = requests.post(
        f"{OPA_URL}/{package}/{rule}",
        json={"input": input_data}
    )
    return response.json()

# Test privacy policy
test_input = {
    "text": "My ID is 8001015009087"
}

result = test_policy("privacy", "allow", test_input)
print(f"Privacy check: {result}")

# Test access policy
test_input = {
    "user": {
        "role": "manager",
        "department": "sales"
    },
    "resource": {
        "department": "sales",
        "public": False
    }
}

result = test_policy("main", "allow_access", test_input)
print(f"Access check: {result}")