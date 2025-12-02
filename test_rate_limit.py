import time
import logging
from scraper import RateLimiter

# Configure logging to see the wait messages
logging.basicConfig(level=logging.INFO)

def test_rate_limiter():
    print("Testing Rate Limiting (5 requests/min = 12s interval)...")
    limiter = RateLimiter(min_interval=2.0) # Use 2s for faster testing, but logic is same
    
    url = "https://example.com/page1"
    
    print(f"Request 1 to {url} at {time.strftime('%X')}")
    limiter.wait(url)
    start = time.time()
    
    print(f"Request 2 to {url} at {time.strftime('%X')}")
    limiter.wait(url)
    elapsed = time.time() - start
    print(f"Elapsed time for Request 2: {elapsed:.2f}s")
    
    if elapsed >= 2.0:
        print("✅ Rate limiting working for same domain.")
    else:
        print("❌ Rate limiting failed for same domain.")
        
    # Test different domain
    url2 = "https://other-domain.com/page1"
    print(f"Request 3 to {url2} at {time.strftime('%X')}")
    start = time.time()
    limiter.wait(url2)
    elapsed = time.time() - start
    print(f"Elapsed time for Request 3 (different domain): {elapsed:.2f}s")
    
    if elapsed < 1.0:
        print("✅ No wait for different domain.")
    else:
        print("❌ Unexpected wait for different domain.")

if __name__ == "__main__":
    test_rate_limiter()
