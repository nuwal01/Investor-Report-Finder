"""
Investor-Report-Finder - Scraping Agent

This module provides functionality to search for and extract investor relations 
reports (annual/quarterly PDFs) from company IR pages.

WARNING:
- MUST FIND MULTIPLE REPORTS (Q1, Q2, Q3) for quarterly requests.
- DO NOT STOP after finding just one report.
- STRICTLY distinguish between 10-K and 10-Q.
"""

import os
import sys
import time
import re
import logging
import argparse
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from pathlib import Path

# Add the backend directory to Python path for Render compatibility
BACKEND_DIR = Path(__file__).parent.absolute()
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from cache_manager import CacheManager
from ticker_parser import TickerParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
SERPER_API_KEY = os.getenv('SERPER_API_KEY')
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
MIN_REQUEST_INTERVAL = 12  # seconds (5 requests per minute)


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass

class IRPageNotFoundError(ScraperError):
    """Raised when IR page cannot be found."""
    pass

class NoReportsFoundError(ScraperError):
    """Raised when no reports are found."""
    pass


class IRReportFinder:
    """
    Main class for finding investor relations reports from company websites.
    """
    
    def __init__(self, api_key: Optional[str] = None, serper_key: Optional[str] = None):
        """
        Initialize the IR report finder.
        
        Args:
            api_key: Optional Tavily API key (will use env var if not provided)
            serper_key: Optional Serper API key (will use env var if not provided)
        """
        self.api_key = api_key or TAVILY_API_KEY
        self.serper_key = serper_key or SERPER_API_KEY
        self.cache = CacheManager()
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
        # Load company name mapping for better ticker matching
        self.company_names = self._load_company_mapping()
        
        # Initialize ticker parser for international market support
        self.ticker_parser = TickerParser()
    
    
    def _load_company_mapping(self) -> Dict[str, List[str]]:
        """Load company name to ticker mapping and create reverse lookup.
        
        Returns:
            Dict mapping ticker to list of company names (e.g., 'AAPL' -> ['apple', 'apple inc'])
        """
        try:
            import json
            # Use absolute path - go up one level from backend/ to project root
            current_dir = Path(__file__).parent
            project_root = current_dir.parent
            mapping_file = project_root / 'company_mapping.json'
            
            if not mapping_file.exists():
                logger.warning(f"Company mapping file not found: {mapping_file}")
                return {}
            
            with open(mapping_file, 'r') as f:
                name_to_ticker = json.load(f)
            
            # Create reverse mapping: ticker -> [company names]
            ticker_to_names = {}
            for company_name, ticker in name_to_ticker.items():
                if ticker not in ticker_to_names:
                    ticker_to_names[ticker] = []
                ticker_to_names[ticker].append(company_name.lower())
            
            return ticker_to_names
        except Exception as e:
            logger.warning(f"Failed to load company mapping: {e}")
            return {}
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()
    
    def _check_robots_txt(self, base_url: str, path: str) -> bool:
        """Check if scraping is allowed by robots.txt."""
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch(USER_AGENT, urljoin(base_url, path))
        except Exception as e:
            logger.warning(f"Could not check robots.txt: {e}")
            return True  # Allow if robots.txt unavailable
    
    def find_ir_page(self, ticker: str) -> Optional[str]:
        """
        Find the investor relations page URL for a given ticker.
        
        Args:
            ticker: Company ticker symbol
            
        Returns:
            URL of the IR page, or None if not found
        """
        if not self.api_key:
            logger.warning("No Tavily API key provided")
            return None
        
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=self.api_key)
            
            # Search for investor relations page
            query = f"{ticker} investor relations annual reports"
            results = tavily.search(query=query, search_depth="basic", max_results=5)
            
            for result in results.get('results', []):
                url = result['url']
                # Check if URL contains investor-relations keywords
                if any(keyword in url.lower() for keyword in ['investor', 'ir', 'annual-report', 'financial']):
                    logger.info(f"Found potential IR page: {url}")
                    return url
            
            logger.warning(f"Could not find IR page for {ticker}")
            return None
            
        except ImportError:
            logger.error("Tavily not installed. Install with: pip install tavily-python")
            return None
        except Exception as e:
            logger.error(f"Error finding IR page: {e}")
            return None
    
    def find_ir_page_via_serper(self, ticker: str) -> Optional[str]:
        """
        Find the investor relations page URL using Serper API (Google Search).
        
        Args:
            ticker: Company ticker symbol
            
        Returns:
            URL of the IR page, or None if not found
        """
        if not self.serper_key:
            logger.warning("No Serper API key provided")
            return None
        
        try:
            # Search for investor relations page using Serper
            query = f"{ticker} investor relations annual reports"
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": self.serper_key,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "gl": "us",
                "hl": "en",
                "num": 5
            }
            
            response = self.session.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            results = response.json()
            
            for result in results.get('organic', []):
                url = result.get('link', '')
                # Check if URL contains investor-relations keywords
                if any(keyword in url.lower() for keyword in ['investor', 'ir', 'annual-report', 'financial']):
                    logger.info(f"Found potential IR page via Serper: {url}")
                    return url
            
            logger.warning(f"Could not find IR page for {ticker} via Serper")
            return None
            
        except Exception as e:
            logger.error(f"Error finding IR page via Serper: {e}")
            return None
    
    def find_reports_via_serper(self, ticker: str, report_type: str, start_year: int, end_year: int) -> List[Dict]:
        """Try to find reports directly using Serper API (Google Search)."""
        if not self.serper_key:
            return []
            
        found_reports = []
        years_to_search = range(end_year, start_year - 1, -1)
        
        try:
            import concurrent.futures
            
            def search_year(year):
                year_reports = []
                try:
                    # Build search query based on report type
                    query_map = {
                        'annual': f'{ticker} {year} "10-K" annual report filetype:pdf',
                        'quarterly': f'{ticker} {year} "10-Q" quarterly report filetype:pdf',
                        'earnings': f"{ticker} {year} earnings release announcement pdf",
                        'presentation': f"{ticker} {year} investor presentation slides pdf",
                        '8-k': f"{ticker} {year} 8-K current report pdf",
                        'financial_statements': f"{ticker} {year} financial statements pdf"
                    }
                    
                    query = query_map.get(report_type, f"{ticker} {year} {report_type} pdf")
                    
                    # Perform Serper search
                    url = "https://google.serper.dev/search"
                    headers = {
                        "X-API-KEY": self.serper_key,
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "q": query,
                        "gl": "us",
                        "hl": "en",
                        "num": 10
                    }
                    
                    response = self.session.post(url, json=payload, headers=headers, timeout=10)
                    response.raise_for_status()
                    results = response.json()
                    
                    for result in results.get('organic', []):
                        serper_result = {
                            'url': result.get('link', ''),
                            'title': result.get('title', '')
                        }
                        processed_report = self._process_tavily_result(serper_result, ticker, year, report_type)
                        if processed_report:
                            # Mark as coming from Serper
                            processed_report['source'] = 'Serper'
                            # Avoid duplicates
                            if not any(r['url'] == processed_report['url'] for r in year_reports):
                                year_reports.append(processed_report)
                    
                    return year_reports
                    
                except Exception as e:
                    logger.warning(f"Serper search failed for {year}: {e}")
                    return []
                return []

            # Execute searches in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_year = {executor.submit(search_year, year): year for year in years_to_search}
                for future in concurrent.futures.as_completed(future_to_year):
                    results = future.result()
                    if results:
                        found_reports.extend(results)
                        
        except Exception as e:
            logger.error(f"Error in find_reports_via_serper: {e}")
            
        return found_reports

    
    def extract_pdf_links(self, url: str) -> List[Dict[str, str]]:
        """
        Extract all PDF links from a given URL.
        
        Args:
            url: URL to extract PDFs from
            
        Returns:
            List of dictionaries containing PDF metadata
        """
        # Check robots.txt
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if not self._check_robots_txt(base_url, parsed_url.path):
            logger.warning(f"Scraping not allowed by robots.txt for {url}")
            return []
        
        # Rate limit
        self._rate_limit()
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            pdfs = []
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Check if it's a PDF
                if href.lower().endswith('.pdf') or '.pdf' in href.lower():
                    # Make absolute URL
                    absolute_url = urljoin(url, href)
                    
                    # Get link text
                    text = link.get_text(strip=True)
                    
                    # Get title attribute if available
                    title = link.get('title', text)
                    
                    pdfs.append({
                        'url': absolute_url,
                        'text': text,
                        'title': title
                    })
            
            logger.info(f"Found {len(pdfs)} PDF links on {url}")
            return pdfs
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing page {url}: {e}")
            return []
    
    def filter_reports(
        self, 
        pdfs: List[Dict[str, str]], 
        ticker: str,
        report_type: str, 
        start_year: int, 
        end_year: int
    ) -> List[Dict[str, str]]:
        """
        Filter PDF reports by type and year range.
        
        Args:
            pdfs: List of PDF metadata dictionaries
            report_type: Report type
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            
        Returns:
            Filtered list of PDF reports with added 'year', 'type' fields
        """
        filtered = []
        
        # Keywords for report types with exclusions to avoid wrong matches
        annual_keywords = ['annual report', '10-k', '10k', 'form 10-k']
        annual_exclusions = ['10-q', '8-k', 'earnings release', 'presentation']
        
        quarterly_keywords = ['10-q', '10q', 'form 10-q', 'quarterly']
        quarterly_exclusions = ['10-k', 'annual report', 'year ended']
        
        earnings_keywords = ['earnings release', 'earnings report', 'earnings announcement', 'quarterly earnings']
        earnings_exclusions = ['10-k', '10-q', 'annual report', 'form 10']
        
        presentation_keywords = ['presentation', 'slide deck', 'investor deck', 'earnings call presentation', 'investor presentation']
        presentation_exclusions = ['10-k', '10-q', 'earnings release']
        
        eight_k_keywords = ['8-k', '8k', 'form 8-k', 'current report']
        eight_k_exclusions = ['10-k', '10-q']
        
        financial_keywords = ['financial statements', 'consolidated financial', 'balance sheet', 'income statement']
        financial_exclusions = []
        
        # Map report type to keywords and exclusions
        type_config_map = {
            'annual': (annual_keywords, annual_exclusions),
            'quarterly': (quarterly_keywords, quarterly_exclusions),
            'earnings': (earnings_keywords, earnings_exclusions),
            'presentation': (presentation_keywords, presentation_exclusions),
            '8-k': (eight_k_keywords, eight_k_exclusions),
            'financial_statements': (financial_keywords, financial_exclusions)
        }
        
        type_keywords, type_exclusions = type_config_map.get(report_type.lower(), (annual_keywords, annual_exclusions))
        
        for pdf in pdfs:
            combined_text = f"{pdf['text']} {pdf['title']} {pdf['url']}".lower()
            
            # Check exclusions first - skip if any exclusion keyword is found
            if any(excl in combined_text for excl in type_exclusions):
                continue
            
            # Check if report type matches
            if not any(keyword in combined_text for keyword in type_keywords):
                continue
            
            # Note: For IR page scraping, we don't strictly enforce ticker presence
            # because IR pages often just say "2023 Annual Report" without the ticker.
            # The strict ticker filtering is applied in _process_tavily_result for web search results.
            
            # Extract year from text
            year_matches = re.findall(r'\b(20[0-9]{2})\b', combined_text)
            
            if year_matches:
                # Get the most recent year mentioned
                year = int(year_matches[-1])
                
                # Check if year is in range
                if start_year <= year <= end_year:
                    pdf_copy = pdf.copy()
                    pdf_copy['year'] = year
                    pdf_copy['type'] = report_type
                    filtered.append(pdf_copy)
        
        # Sort by year (most recent first)
        filtered.sort(key=lambda x: x['year'], reverse=True)
        
        logger.info(f"Filtered to {len(filtered)} reports matching criteria")
        return filtered

    def _identify_quarter(self, text: str) -> Optional[str]:
        """Identify quarter from text (Q1, Q2, Q3). Q4 is usually 10-K."""
        text = text.lower()
        if 'q1' in text or 'first quarter' in text or '1st quarter' in text or 'march 31' in text:
            return 'Q1'
        if 'q2' in text or 'second quarter' in text or '2nd quarter' in text or 'june 30' in text:
            return 'Q2'
        if 'q3' in text or 'third quarter' in text or '3rd quarter' in text or 'september 30' in text:
            return 'Q3'
        # Q4 is typically covered in Annual Report (10-K)
        return None

    def _get_missing_quarters(self, reports: List[Dict], year: int) -> List[str]:
        """Identify which quarters are missing for a given year."""
        found_quarters = set()
        for r in reports:
            if r['year'] == year and r.get('quarter'):
                found_quarters.add(r['quarter'])
        
        expected_quarters = {'Q1', 'Q2', 'Q3'}
        missing = list(expected_quarters - found_quarters)
        missing.sort()
        return missing
    
    def find_reports_via_tavily(self, ticker: str, report_type: str, start_year: int, end_year: int) -> List[Dict]:
        """Try to find reports directly using Tavily search with multi-method strategy."""
        if not self.api_key:
            return []
            
        found_reports = []
        years_to_search = range(end_year, start_year - 1, -1)
        
        try:
            from tavily import TavilyClient
            import concurrent.futures
            tavily = TavilyClient(api_key=self.api_key)
            
            def search_year(year):
                year_reports = []
                try:
                    # METHOD 1: BROAD SEARCH
                    # Use ticker_parser for country-specific queries
                    enhanced_query = self.ticker_parser.build_search_query(
                        ticker=ticker,
                        year=year,
                        report_type=report_type
                    )
                    
                    # Perform Broad Search
                    results = tavily.search(query=enhanced_query, search_depth="advanced", max_results=20)
                    
                    for result in results.get('results', []):
                        processed_report = self._process_tavily_result(result, ticker, year, report_type)
                        if processed_report:
                            # Avoid duplicates
                            if not any(r['url'] == processed_report['url'] for r in year_reports):
                                year_reports.append(processed_report)
                    
                    # METHOD 2: GAP ANALYSIS & TARGETED FALLBACK (Only for Quarterly)
                    if report_type == 'quarterly':
                        missing_quarters = self._get_missing_quarters(year_reports, year)
                        
                        if missing_quarters:
                            logger.info(f"Year {year}: Missing quarters {missing_quarters}. Initiating targeted search.")
                            
                            for quarter in missing_quarters:
                                # Targeted query for specific quarter
                                targeted_query = f'{ticker} {year} {quarter} "10-Q" quarterly report filetype:pdf -10-K'
                                try:
                                    q_results = tavily.search(query=targeted_query, search_depth="advanced", max_results=5)
                                    for result in q_results.get('results', []):
                                        processed_report = self._process_tavily_result(result, ticker, year, report_type)
                                        if processed_report and processed_report.get('quarter') == quarter:
                                             if not any(r['url'] == processed_report['url'] for r in year_reports):
                                                year_reports.append(processed_report)
                                                logger.info(f"Found missing {quarter} for {year}")
                                                break # Found the missing quarter, move to next
                                except Exception as e:
                                    logger.warning(f"Targeted search failed for {year} {quarter}: {e}")

                    return year_reports
                    
                except Exception as e:
                    logger.warning(f"Tavily search failed for {year}: {e}")
                    return []
                return []

            # Execute searches in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_year = {executor.submit(search_year, year): year for year in years_to_search}
                for future in concurrent.futures.as_completed(future_to_year):
                    results = future.result()
                    if results:
                        found_reports.extend(results)
                        
        except ImportError:
            logger.warning("Tavily not installed, skipping direct search")
        except Exception as e:
            logger.error(f"Error in find_reports_via_tavily: {e}")
            
        return found_reports

    def _process_tavily_result(self, result: Dict, ticker: str, year: int, report_type: str) -> Optional[Dict]:
        """Helper to process and validate a single Tavily result."""
        url = result['url']
        title = result['title']
        
        # Check if it looks like a PDF
        is_pdf = url.lower().endswith('.pdf') or 'pdf' in title.lower()
        is_sec = 'sec.gov' in url.lower()
        
        # STRICT FILTERING: Exclude wrong report types
        combined_text = f"{title} {url}".lower()
        
        # For quarterly reports, exclude annual reports
        if report_type == 'quarterly':
            # Exclude if any annual report indicators are present
            if any(keyword in combined_text for keyword in ['10-k', '10k', 'annual report', 'form 10-k', 'year ended']):
                return None
            # Require quarterly indicators
            if not any(keyword in combined_text for keyword in ['10-q', '10q', 'quarterly', 'form 10-q']):
                return None
            
            # Identify quarter
            quarter = self._identify_quarter(combined_text)
            if not quarter:
                # If we can't identify Q1-Q3, it might be a Q4/Annual misidentified or just generic
                if 'q4' in combined_text or 'fourth quarter' in combined_text:
                    return None
        
        # For annual reports, exclude quarterly reports
        if report_type == 'annual':
            # Exclude if any quarterly report indicators are present
            if any(keyword in combined_text for keyword in ['10-q', '10q', 'quarterly report', 'form 10-q', 'first quarter', 'second quarter', 'third quarter']):
                return None
            # Require annual indicators (but not for SEC links which may have generic names)
            if not is_sec and not any(keyword in combined_text for keyword in ['10-k', '10k', 'annual report', 'form 10-k']):
                return None
        
        # For earnings, exclude 10-K and 10-Q to avoid wrong matches
        if report_type == 'earnings':
            if '10-k' in combined_text or '10-q' in combined_text or 'form 10' in combined_text:
                return None
        
        # For presentations, require presentation keywords
        if report_type == 'presentation':
            if not any(kw in combined_text for kw in ['presentation', 'slides', 'deck', 'investor']):
                return None
        
        
        if is_pdf or is_sec:
            # Verify year is in title or URL
            year_str = str(year)
            if year_str in title or year_str in url:
                # STRICT FILTERING: Enforce ticker OR company name presence for Tavily results
                # SEC.gov URLs are authoritative, so we can be less strict
                if 'sec.gov' not in url.lower():
                    # For non-SEC URLs, check if ticker or company name appears
                    # Use word boundary matching to avoid false positives like "CMI" matching "Carbon Mitigation Initiative"
                    ticker_pattern = r'\b' + re.escape(ticker.lower()) + r'\b'
                    ticker_found = re.search(ticker_pattern, combined_text)
                    
                    # Also check if any company name variant appears
                    company_names = self.company_names.get(ticker.upper(), [])
                    company_found = any(company_name in combined_text for company_name in company_names)
                    
                    # ULTRA-STRICT for very short tickers (2-3 chars) to avoid acronym confusion
                    # e.g., "CMI" could be Cummins OR Carbon Mitigation Initiative OR Count Me In!
                    if len(ticker) <= 3:
                        # For short tickers, require BOTH ticker AND company name
                        # OR ticker in corporate context (e.g., "CMI Inc", "investor.cummins.com")
                        corporate_context = bool(re.search(
                            r'\b' + re.escape(ticker.lower()) + r'\s+(inc\.?|corp\.?|corporation|limited|ltd\.?)\b',
                            combined_text
                        ))
                        
                        # Check if URL is from company's investor domain
                        investor_domain = any(
                            comp_name.replace(' ', '').replace('.', '').lower() in url.lower()
                            for comp_name in company_names
                        )
                        
                        # Require: (ticker AND company name) OR corporate context OR investor domain
                        if not ((ticker_found and company_found) or corporate_context or investor_domain):
                            # Likely a false positive (acronym for different organization)
                            return None
                    else:
                        # For longer tickers (4+ chars), original logic: ticker OR company name
                        if not (ticker_found or company_found):
                            # Neither ticker nor company name found - likely unrelated
                            return None

                # logger.info(f"Found {report_type} report via Tavily: {title}") # Reduced logging
                report_data = {
                    'url': url,
                    'text': title,
                    'title': title,
                    'year': year,
                    'type': report_type
                }
                if report_type == 'quarterly':
                    report_data['quarter'] = self._identify_quarter(combined_text)
                
                return report_data
        return None



    
    def search_reports(self, ticker: str, report_type: str = 'annual', start_year: int = 2020, end_year: int = 2024) -> List[Dict]:
        """Search for reports for a specific company and time range."""
        logger.info(f"Searching for {report_type} reports for {ticker} ({start_year}-{end_year})")
        
        try:
            # Step 0: Check cache for reports
            cached_reports = self.cache.get_reports(ticker, report_type, start_year, end_year)
            if cached_reports:
                logger.info(f"Found {len(cached_reports)} reports in cache")
                return cached_reports
            
            # Step 1: Try parallel search via Tavily AND Serper (combine results)
            logger.info("Attempting parallel search via Tavily and Serper...")
            
            import concurrent.futures
            all_reports = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both searches in parallel
                futures = {}
                if self.api_key:
                    futures['tavily'] = executor.submit(self.find_reports_via_tavily, ticker, report_type, start_year, end_year)
                if self.serper_key:
                    futures['serper'] = executor.submit(self.find_reports_via_serper, ticker, report_type, start_year, end_year)
                
                # Collect results as they complete
                for source, future in futures.items():
                    try:
                        reports = future.result()
                        if reports:
                            logger.info(f"Found {len(reports)} reports via {source.capitalize()}")
                            all_reports.extend(reports)
                    except Exception as e:
                        logger.warning(f"{source.capitalize()} search failed: {e}")
            
            # Deduplicate reports by URL
            if all_reports:
                seen_urls = set()
                unique_reports = []
                for report in all_reports:
                    if report['url'] not in seen_urls:
                        seen_urls.add(report['url'])
                        unique_reports.append(report)
                
                # For annual reports, ensure we only have ONE report per year
                # (Take the first one found, which is typically the most relevant)
                if report_type == 'annual':
                    seen_years = set()
                    final_reports = []
                    # Sort by year desc so we process most recent first
                    unique_reports.sort(key=lambda x: x.get('year', 0), reverse=True)
                    for report in unique_reports:
                        year = report.get('year')
                        if year and year not in seen_years:
                            seen_years.add(year)
                            final_reports.append(report)
                    unique_reports = final_reports
                
                logger.info(f"Found {len(unique_reports)} unique reports via direct search (combined Tavily + Serper)")
                self.cache.save_reports(ticker, unique_reports)
                return unique_reports
            
            logger.info("Direct search yielded no results. Falling back to IR page scraping.")
            
            # Step 2: Fallback - Find IR page via Tavily, if that fails try Serper
            ir_url = None
            if self.api_key:
                ir_url = self.find_ir_page(ticker)
            
            if not ir_url and self.serper_key:
                logger.info("Tavily IR page search failed, trying Serper...")
                ir_url = self.find_ir_page_via_serper(ticker)
            
            if not ir_url:
                logger.warning(f"Could not find IR page for {ticker}")
                return []
            
            # Step 3: Extract PDF links
            pdf_links = self.extract_pdf_links(ir_url)
            if not pdf_links:
                logger.warning("No PDF links found on IR page")
                return []
            
            # Step 4: Filter by type and year
            filtered_reports = self.filter_reports(pdf_links, ticker, report_type, start_year, end_year)
            
            if not filtered_reports:
                logger.info(f"No matching {report_type} reports found in range {start_year}-{end_year}")
            else:
                logger.info(f"Found {len(filtered_reports)} matching reports")
            
            # Step 5: Save to cache
            if filtered_reports:
                self.cache.save_reports(ticker, filtered_reports)
            
            return filtered_reports
            
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            return []
    
    def search_from_parsed_prompt(self, parsed_data: Dict) -> List[Dict[str, str]]:
        """Convenience method to search using data from prompt parser."""
        if 'error' in parsed_data:
            logger.error(f"Error in parsed data: {parsed_data['error']}")
            return []
        
        if not parsed_data.get('ticker'):
            logger.error("Error: No ticker symbol found in parsed data")
            return []
        
        return self.search_reports(
            ticker=parsed_data['ticker'],
            report_type=parsed_data.get('report_type', 'annual'),
            start_year=parsed_data.get('start_year', 2024),
            end_year=parsed_data.get('end_year', 2024)
        )


def main():
    """Command-line interface for the scraper."""
    parser = argparse.ArgumentParser(description='Search for investor relations reports')
    parser.add_argument('--ticker', required=True, help='Company ticker symbol (e.g., AAPL)')
    parser.add_argument('--type', choices=['annual', 'quarterly', 'earnings', 'presentation', '8-k', 'financial_statements'], 
                       default='annual', help='Report type')
    parser.add_argument('--start-year', type=int, default=2020, help='Start year')
    parser.add_argument('--end-year', type=int, default=2024, help='End year')
    
    args = parser.parse_args()
    
    # Create finder and search
    finder = IRReportFinder()
    reports = finder.search_reports(
        ticker=args.ticker,
        report_type=args.type,
        start_year=args.start_year,
        end_year=args.end_year
    )
    
    # Display results
    print(f"\n{'='*60}")
    print(f"RESULTS: Found {len(reports)} matching reports")
    print(f"{'='*60}\n")
    
    for i, report in enumerate(reports, 1):
        print(f"{i}. Year: {report['year']} | Type: {report['type']}")
        print(f"   Title: {report['text'][:100]}")
        print(f"   URL: {report['url']}")
        print()


if __name__ == '__main__':
    main()
