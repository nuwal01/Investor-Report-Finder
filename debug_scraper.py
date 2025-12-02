import logging
import os
from dotenv import load_dotenv
from scraper import IRReportFinder

# Configure logging to show our new debug messages
logging.basicConfig(level=logging.INFO)

def debug_search():
    load_dotenv()
    api_key = os.getenv('TAVILY_API_KEY')
    print(f"Tavily API Key present: {bool(api_key)}")
    
    finder = IRReportFinder()
    
    # Test with AAPL 2020-2022
    print("\n--- Debugging Search for AAPL 2020-2022 ---")
    reports = finder.search_reports("AAPL", "annual", 2020, 2022)
    
    print("\n--- Final Results ---")
    for r in reports:
        print(r)

if __name__ == "__main__":
    debug_search()
