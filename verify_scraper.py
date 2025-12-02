
import sys
import os
import logging
from scraper import IRReportFinder

# Configure logging
logging.basicConfig(level=logging.INFO)


def test_scraper():
    # Clear cache first
    try:
        cache_path = os.path.join(os.path.dirname(__file__), "backend", "cache.db")
        if os.path.exists(cache_path):
            os.remove(cache_path)
            print("Cache cleared.")
        else:
            # Try alternate location
            cache_path = os.path.join(os.path.dirname(__file__), "cache.db")
            if os.path.exists(cache_path):
                os.remove(cache_path)
                print("Cache cleared.")
    except Exception as e:
        print(f"Warning: Could not clear cache: {e}")

    finder = IRReportFinder()
    
    print("\n" + "="*60)
    print("TEST 1: Searching for Apple 2023 Quarterly Reports (Expect Q1, Q2, Q3)")
    print("="*60)
    reports = finder.search_reports(ticker="AAPL", report_type="quarterly", start_year=2023, end_year=2023)
    
    q_count = 0
    k_count = 0
    found_quarters = set()
    
    for r in reports:
        title = r.get('text', r.get('title', '')).lower()
        print(f"Found: {title} ({r['type']}) - Quarter: {r.get('quarter')}")
        
        if '10-k' in title or 'annual' in title:
            k_count += 1
            print("  >>> ERROR: FOUND 10-K IN QUARTERLY SEARCH!")
        elif '10-q' in title or 'quarterly' in title:
            q_count += 1
            if r.get('quarter'):
                found_quarters.add(r['quarter'])
            
    print(f"\nSummary: 10-Qs: {q_count}, 10-Ks: {k_count}")
    print(f"Quarters Found: {sorted(list(found_quarters))}")
    
    if k_count == 0 and len(found_quarters) >= 3:
        print("[PASS] TEST 1 PASSED (Found all 3 quarters)")
    elif k_count == 0 and q_count > 0:
        print("[WARN] TEST 1 PARTIAL PASS (Found some quarters but not all 3)")
    else:
        print("[FAIL] TEST 1 FAILED")

    print("\n" + "="*60)
    print("TEST 2: Searching for Microsoft 2023 Annual Reports (Expect 10-K, NO 10-Qs)")
    print("="*60)
    reports = finder.search_reports(ticker="MSFT", report_type="annual", start_year=2023, end_year=2023)
    
    q_count = 0
    k_count = 0
    
    for r in reports:
        title = r.get('text', r.get('title', '')).lower()
        print(f"Found: {title} ({r['type']})")
        
        if '10-k' in title or 'annual' in title:
            k_count += 1
        elif '10-q' in title or 'quarterly' in title:
            q_count += 1
            print("  >>> ERROR: FOUND 10-Q IN ANNUAL SEARCH!")
            
    print(f"\nSummary: 10-Qs: {q_count}, 10-Ks: {k_count}")
    if q_count == 0 and k_count > 0:
        print("[PASS] TEST 2 PASSED")
    else:
        print("[FAIL] TEST 2 FAILED")

if __name__ == "__main__":
    test_scraper()
