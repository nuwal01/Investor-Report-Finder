import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

from backend.main import app

client = TestClient(app)

def test_resolve_endpoint():
    response = client.post("/api/resolve-company", json={"query": "Apple", "max_results": 5})
    assert response.status_code == 200
    data = response.json()
    assert data['success'] == True
    assert len(data['matches']) > 0
    assert 'exchange' in data['matches'][0]

def test_verify_endpoint():
    response = client.post("/api/verify-company", json={"ticker": "AAPL", "company_name": "Apple Inc."})
    assert response.status_code == 200
    data = response.json()
    assert data['is_valid'] == True
    assert data['ticker'] == "AAPL"

def test_verify_endpoint_mismatch():
    response = client.post("/api/verify-company", json={"ticker": "MSFT", "company_name": "Apple Inc."})
    assert response.status_code == 200
    data = response.json()
    assert data['is_valid'] == False
