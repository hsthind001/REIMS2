import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_current_user

# Mock authentication
async def mock_get_current_user():
    return {"id": 1, "email": "test@example.com", "role": "admin"}

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

def test_evaluate_calculated_rules():
    PROPERTY_ID = 11
    PERIOD_ID = 169
    
    print(f"\nTesting /api/v1/forensic-reconciliation/calculated-rules/evaluate/{PROPERTY_ID}/{PERIOD_ID}")
    
    response = client.get(f"/api/v1/forensic-reconciliation/calculated-rules/evaluate/{PROPERTY_ID}/{PERIOD_ID}")
    
    if response.status_code != 200:
        print(f"FAILED: Status {response.status_code}")
        print(response.content)
        return

    data = response.json()
    print(f"Success! Status 200")
    print(f"Total Rules: {data.get('total')}")
    print(f"Passed: {data.get('passed')}")
    print(f"Failed: {data.get('failed')}")
    
    rules = data.get('rules', [])
    if rules:
        print("\nSample Rule:")
        print(rules[0])
    else:
        print("\nNo rules returned!")

if __name__ == "__main__":
    test_evaluate_calculated_rules()
