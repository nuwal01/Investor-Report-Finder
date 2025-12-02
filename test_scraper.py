"""
Test script to verify PDF extraction from known IR pages.
"""

from scraper import IRReportFinder

def test_with_known_url():
    """Test PDF extraction with a known IR page URL."""
    
    finder = IRReportFinder()
    
    # Test with Apple's actual investor relations page
    test_cases = [
        {
            'name': 'Apple',
            'ticker': 'AAPL',
            'url': 'https://investor.apple.com/investor-relations/default.aspx',
            'type': 'annual',
            'years': (2022, 2024)
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing {test['name']} ({test['ticker']})")
        print(f"URL: {test['url']}")
        print(f"{'='*60}\n")
        
        # Extract PDFs
        pdfs = finder.extract_pdf_links(test['url'])
        print(f"\nTotal PDFs found: {len(pdfs)}")
        
        # Filter reports
        filtered = finder.filter_reports(
            pdfs, 
            test['type'], 
            test['years'][0], 
            test['years'][1]
        )
        
        print(f"\n{'='*60}")
        print(f"FILTERED RESULTS: {len(filtered)} matching reports")
        print(f"{'='*60}\n")
        
        for i, report in enumerate(filtered, 1):
            print(f"{i}. Year: {report['year']} | Type: {report['type']}")
            print(f"   Title: {report['text'][:80]}")
            print(f"   URL: {report['url']}")
            print()

if __name__ == '__main__':
    test_with_known_url()
