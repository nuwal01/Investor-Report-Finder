import os
import time
import sqlite3
from scraper import IRReportFinder
from cache_manager import CacheManager

def test_caching():
    print("Testing Caching Mechanism (Seeded)...")
    
    # Initialize
    finder = IRReportFinder()
    ticker = "TEST_TICKER"
    fake_url = "https://example.com/ir"
    
    # Clear existing cache
    if os.path.exists(finder.cache.db_path):
        try:
            os.remove(finder.cache.db_path)
        except:
            pass
    
    # Re-init to create DB
    finder = IRReportFinder()
    
    # Manually seed the cache
    print(f"Seeding cache for {ticker} -> {fake_url}")
    finder.cache.save_ir_page(ticker, fake_url)
    
    # Verify DB content directly
    conn = sqlite3.connect(finder.cache.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM ir_pages WHERE ticker=?", (ticker,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0] == fake_url:
        print("✅ Database write verified.")
    else:
        print("❌ Database write failed.")
        return

    # Test Cache Hit in Scraper
    print("\n--- Testing Scraper Cache Hit ---")
    start_time = time.time()
    found_url = finder.find_ir_page(ticker)
    duration = time.time() - start_time
    
    if found_url == fake_url:
        print(f"✅ Scraper returned cached URL: {found_url}")
    else:
        print(f"❌ Scraper failed to return cached URL. Got: {found_url}")
        
    if duration < 0.1:
        print(f"✅ Performance check passed ({duration:.4f}s)")
    else:
        print(f"⚠️ Performance check slow ({duration:.4f}s)")

if __name__ == "__main__":
    test_caching()
