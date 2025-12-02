import logging
import os
from scraper import IRReportFinder

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_tavily_direct_search():
    print("Testing Tavily Direct Search...")
    
    # Ensure API key is present (or mock it if we want to test logic without API)
    # For this test, we assume the environment has the key or we rely on fallback behavior if missing
    
    finder = IRReportFinder()
    
    # We'll test with a common ticker
    ticker = "NVDA"
    
    # Clear cache for this test to force search
    # (In a real test we might want to be more careful, but here we want to see the search happen)
    
    print(f"\n--- Searching for {ticker} 2023 Annual Report ---")
    reports = finder.search_reports(ticker, "annual", 2023, 2023)
    
    if reports:
        print(f"✅ Found {len(reports)} reports.")
        for r in reports:
            print(f"   - {r['year']} {r['type']}: {r['title']} ({r['url']})")
    else:
        print("❌ No reports found.")

if __name__ == "__main__":
    test_tavily_direct_search()
