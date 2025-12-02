import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

from backend.company_resolver import CompanyResolver

def test_resolver_initialization():
    resolver = CompanyResolver()
    assert resolver.company_mapping is not None

def test_resolve_exact_ticker():
    resolver = CompanyResolver()
    matches = resolver.resolve("AAPL")
    assert len(matches) > 0
    assert matches[0]['ticker'] == "AAPL"
    assert matches[0]['exchange'] == "NASDAQ"

def test_resolve_international_ticker():
    resolver = CompanyResolver()
    matches = resolver.resolve("RELIANCE.NS")
    assert len(matches) > 0
    assert matches[0]['ticker'] == "RELIANCE.NS"
    assert matches[0]['country'] == "India"

def test_ambiguity_detection():
    resolver = CompanyResolver()
    # Samsung matches multiple companies
    is_ambiguous = resolver.detect_ambiguity("Samsung")
    assert is_ambiguous == True
    
    # Apple matches specifically Apple Inc. (high confidence)
    is_not_ambiguous = resolver.detect_ambiguity("Apple Inc.")
    assert is_not_ambiguous == False

def test_verify_match():
    resolver = CompanyResolver()
    # Valid match
    result = resolver.verify_match("AAPL", "Apple Inc.")
    assert result['is_valid'] == True
    
    # Invalid match
    result = resolver.verify_match("MSFT", "Apple Inc.")
    assert result['is_valid'] == False
