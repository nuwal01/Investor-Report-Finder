"""
OpenAI + OpenRouter Hybrid Report Finder

Uses OpenRouter (ChatGPT/Claude) for comprehensive document discovery
with Serper API as fallback for URL validation/additional search.
"""

import os
import re
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Import OpenRouter fallback
try:
    from openrouter_fallback import OpenRouterFallbackRetriever
except ImportError:
    OpenRouterFallbackRetriever = None


class OpenAISerperReportFinder:
    """
    Find investor relations reports using OpenRouter (primary) + Serper (fallback).
    """
    
    def __init__(self, openai_key: Optional[str] = None, serper_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the hybrid report finder.
        
        Args:
            openai_key: OpenAI API key (optional, uses env var if not provided)
            serper_key: Serper API key (optional, uses env var if not provided)
            base_url: Custom OpenAI base URL (optional, e.g. for OpenRouter)
        """
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.serper_key = serper_key or os.getenv("SERPER_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        
        # Initialize OpenRouter retriever as primary
        self.openrouter_retriever = None
        if OpenRouterFallbackRetriever:
            try:
                self.openrouter_retriever = OpenRouterFallbackRetriever()
                print("[+] OpenRouter initialized as PRIMARY search method")
            except Exception as e:
                print(f"Warning: Could not initialize OpenRouter: {e}")
        
        # Initialize OpenAI for query parsing
        self.openai_client = None
        if self.openai_key and OpenAI:
            try:
                self.openai_client = OpenAI(
                    api_key=self.openai_key,
                    base_url=self.base_url
                )
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI: {e}")
    
    def find_reports(self, prompt: str) -> Dict:
        """
        Find investor reports using Serper (primary) + OpenRouter (fallback).
        
        Args:
            prompt: Natural language query (e.g., "Annual reports for Apple from 2020 to 2024")
        
        Returns:
            Dict with:
                - reports: List of report dictionaries
                - missing_years: Years requested but not found
                - requested_years: Original years requested
                - source_pages: Categorized source page URLs
        """
        print(f"\n{'='*60}")
        print(f"Processing prompt: {prompt}")
        print(f"{'='*60}")
        
        # STEP 0: Check if user provided a reports URL directly
        user_provided_url = self._extract_url_from_prompt(prompt)
        if user_provided_url:
            print(f"\n[STEP 0] User provided URL detected: {user_provided_url}")
            return self._extract_from_user_url(prompt, user_provided_url)
        
        # Step 1: Parse query
        parsed = self._parse_query(prompt)
        print(f"\nParsed query:")
        print(f"  Company: {parsed.get('company')}")
        print(f"  Report Type: {parsed.get('report_type')}")
        print(f"  Years: {parsed.get('years')}")
        print(f"  Quarters: {parsed.get('quarters')}")
        
        if not parsed.get('company'):
            raise ValueError("Could not identify company from prompt")
        
        requested_years = parsed.get('years', [datetime.now().year])
        start_year = min(requested_years)
        end_year = max(requested_years)
        report_type = parsed.get('report_type', 'annual')
        requested_quarters = parsed.get('quarters')  # ['Q1'], ['Q1','Q2','Q3','Q4'], or None
        
        # Initialize output structure
        reports = []
        reports_pages = []
        official_website = ''
        official_investor_relations = ''
        notes_list = []
        
        # ============================================
        # STRICT RETRIEVAL LADDER
        # ============================================
        
        # STEP 1: Find official domain and IR page via Serper
        if self.serper_key:
            print(f"\n[STEP 1] Finding official company website...")
            ir_page = self._find_investor_relations_page(parsed['company'])
            if ir_page:
                official_investor_relations = ir_page
                # Extract official website from IR page
                from urllib.parse import urlparse
                parsed_url = urlparse(ir_page)
                official_website = f"{parsed_url.scheme}://{parsed_url.netloc}"
                print(f"  Found: {official_website}")
                notes_list.append(f"Found official IR: {ir_page}")
            
            # STEP 2: Search for reports pages
            print(f"\n[STEP 2] Searching for reports listing pages...")
            reports_pages = self._find_reports_pages(parsed['company'], official_website)
            if reports_pages:
                notes_list.append(f"Found {len(reports_pages)} reports pages")
                for rp in reports_pages:
                    print(f"  Found {rp['doc_category']}: {rp['url']}")
            
            # FALLBACK: If no reports pages but have IR page, add it as fallback
            if not reports_pages and official_investor_relations:
                reports_pages = [{'doc_category': 'Investor Relations', 'url': official_investor_relations}]
                print(f"  Fallback: Using IR page as reports page")
        
        # STEP 3: Search for PDFs using Serper (primary)
        if self.serper_key:
            print(f"\n[STEP 3] Searching for PDF documents...")
            serper_reports = self._search_with_serper(
                company=parsed['company'],
                report_type=report_type,
                years=requested_years,
                requested_quarters=requested_quarters
            )
            reports.extend(serper_reports)
            print(f"[SERPER] Found {len(serper_reports)} documents")
            if serper_reports:
                notes_list.append(f"Serper found {len(serper_reports)} PDFs")
        
        # Calculate missing years after Serper
        found_years = set(r.get('year') for r in reports if r.get('type') != 'investor_relations_page')
        missing_years = sorted([y for y in requested_years if y not in found_years])
        
        # STEP 4: Site-restricted search if missing years
        if missing_years and self.serper_key and official_website:
            print(f"\n[STEP 4] Site-restricted search for missing years: {missing_years}")
            site_domain = urlparse(official_website).netloc
            for year in missing_years:
                site_reports = self._search_site_restricted(
                    site_domain, parsed['company'], report_type, year
                )
                if site_reports:
                    reports.extend(site_reports)
                    notes_list.append(f"Site search found {len(site_reports)} for {year}")
        
        # Recalculate missing years
        found_years = set(r.get('year') for r in reports if r.get('type') != 'investor_relations_page')
        missing_years = sorted([y for y in requested_years if y not in found_years])
        
        # STEP 5: OpenRouter fallback if still missing
        if (not reports or missing_years) and self.openrouter_retriever:
            print(f"\n[STEP 5] OpenRouter AI fallback...")
            try:
                doc_types = self._get_doc_types(report_type)
                
                result = self.openrouter_retriever.retrieve_documents(
                    company=parsed['company'],
                    doc_types=doc_types,
                    start_year=start_year,
                    end_year=end_year,
                )
                
                # Use OpenRouter's official website if we don't have one
                if not official_website and result.get('official_website'):
                    official_website = result.get('official_website')
                if not official_investor_relations and result.get('official_investor_relations'):
                    official_investor_relations = result.get('official_investor_relations')
                
                # Add OpenRouter reports_pages
                if result.get('reports_pages'):
                    for rp in result.get('reports_pages', []):
                        if rp not in reports_pages:
                            reports_pages.append(rp)
                
                # Add OpenRouter documents for missing years only
                for doc in result.get('documents', []):
                    doc_year = self._extract_year(doc.get('period', ''))
                    if doc_year in missing_years:
                        reports.append({
                            'year': doc_year,
                            'type': doc.get('doc_type', report_type),
                            'title': doc.get('title', ''),
                            'url': doc.get('pdf_url', ''),
                            'source_page': doc.get('source_page', ''),
                            'source': 'openrouter'
                        })
                
                if result.get('notes') and 'error' not in result.get('notes', '').lower():
                    notes_list.append(f"OpenRouter: {result.get('notes')}")
                
                print(f"[OPENROUTER] Added documents from AI fallback")
                
            except Exception as e:
                print(f"[OPENROUTER] Error: {e}")
                # Don't show raw errors to users - just log them
        
        # Recalculate missing years
        found_years = set(r.get('year') for r in reports if r.get('type') != 'investor_relations_page')
        missing_years = sorted([y for y in requested_years if y not in found_years])
        
        # STEP 6: DISABLED - AI analysis was too slow
        # if not reports or missing_years:
        #     print(f"\n[STEP 6] Analyzing why reports weren't found...")
        #     reason_note = self._analyze_missing_reports(...)
        #     if reason_note:
        #         notes_list.insert(0, reason_note)
        
        # Build notes string
        notes = ". ".join(notes_list) if notes_list else "Search completed"
        
        # Log results
        print(f"\n[OK] FINAL RESULTS: Found {len(reports)} total results")
        print(f"   Company: {parsed['company']}")
        print(f"   Official website: {official_website}")
        print(f"   Reports pages: {len(reports_pages)}")
        print(f"   Requested years: {requested_years}")
        print(f"   Found years: {sorted(found_years)}")
        if missing_years:
            print(f"   ⚠️ Missing years: {missing_years}")
        
        # Calculate missing periods (quarters for quarterly, years for annual)
        missing_periods = []
        if report_type == 'quarterly' and requested_quarters:
            # For quarterly: check each (year, quarter) pair
            found_periods = set()
            for r in reports:
                if r.get('quarter') and r.get('year'):
                    found_periods.add((r.get('year'), r.get('quarter')))
            
            for year in requested_years:
                for quarter in requested_quarters:
                    if (year, quarter.upper()) not in found_periods:
                        missing_periods.append(f"{quarter.upper()} {year}")
            
            print(f"   Found periods: {sorted(found_periods) if found_periods else 'None'}")
        else:
            # For annual: missing_periods = missing_years formatted
            missing_periods = [f"FY{y}" for y in missing_years]
        
        if missing_periods:
            print(f"   ⚠️ Missing periods: {missing_periods}")
        
        # Build request structure for output
        request_info = {
            'doc_type': report_type,
            'periods': []
        }
        if report_type == 'quarterly' and requested_quarters:
            for year in requested_years:
                for quarter in requested_quarters:
                    request_info['periods'].append(f"{quarter.upper()} {year}")
        else:
            request_info['periods'] = [f"FY{y}" for y in requested_years]
        
        return {
            'company': parsed['company'],
            'request': request_info,  # New: structured request info
            'official_website': official_website,
            'official_investor_relations': official_investor_relations,
            'reports_pages': reports_pages,
            'reports': reports,
            'missing_years': missing_years,  # Keep for backwards compatibility
            'missing_periods': missing_periods,  # New: period-aware missing list
            'requested_years': list(requested_years),
            'requested_quarters': requested_quarters or [],  # New: requested quarters
            'notes': notes
        }
    
    def _get_doc_types(self, report_type: str) -> List[str]:
        """Map report type to list of document types for OpenRouter."""
        type_mapping = {
            'annual': ['annual report', '10-K', '20-F', 'financial statements'],
            'quarterly': ['quarterly report', '10-Q', 'interim report', 'Q1', 'Q2', 'Q3', 'Q4'],
            'earnings': ['earnings release', 'earnings report', 'press release', 'results announcement'],
            'presentation': ['investor presentation', 'earnings presentation'],
            '10-k': ['10-K', 'annual report'],
            '10-q': ['10-Q', 'quarterly report'],
            'financial_statements': ['financial statements', 'annual report', 'quarterly report'],
        }
        return type_mapping.get(report_type.lower(), ['annual report', 'quarterly report', 'earnings release'])
    
    def _analyze_missing_reports(self, company: str, report_type: str, missing_years: List[int]) -> str:
        """
        Use AI to analyze why reports couldn't be found and provide a specific explanation.
        Returns a user-friendly reason note.
        """
        if not self.openai_client:
            return "Reports not found - AI analysis unavailable"
        
        try:
            prompt = f"""Analyze why {report_type} reports for "{company}" might not be found for years {missing_years}.

Research this company and provide a SPECIFIC explanation. Consider:
1. Is this a holding company that doesn't publish consolidated reports?
2. Do they publish through subsidiaries only?
3. Are reports only available in a different language or format?
4. Is the company private or delisted?
5. Do they use a different reporting calendar?
6. Are reports behind a login/paywall?

Respond with ONE concise sentence starting with "I found the issue:" that explains the SPECIFIC reason.
If you don't know, say "Reports may not be publicly available for this company - check their official IR page."
Do NOT say generic things like "not found" or "unavailable"."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a financial research assistant. Provide specific, actionable explanations for why investor reports might not be found."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150,
                timeout=10
            )
            
            reason = response.choices[0].message.content.strip()
            print(f"  AI Analysis: {reason}")
            return reason
            
        except Exception as e:
            print(f"  AI Analysis failed: {e}")
            return f"Reports for {company} ({missing_years}) could not be located - please check the company's official investor relations page"
    
    def _extract_year(self, period: str) -> int:
        """Extract year from period string like 'FY2023' or 'Q1 2024'."""
        match = re.search(r'(20\d{2})', period)
        if match:
            return int(match.group(1))
        return datetime.now().year
    
    def _extract_url_from_prompt(self, prompt: str) -> Optional[str]:
        """
        Extract URL from user's prompt if one is provided.
        Returns URL if it looks like a reports/financial page.
        """
        # Find all URLs in the prompt
        url_pattern = r'https?://[^\s<>"\'()]+'
        urls = re.findall(url_pattern, prompt)
        
        if not urls:
            return None
        
        # Check if any URL looks like a reports page
        reports_keywords = ['report', 'financial', 'result', 'investor', 
                           'filing', 'disclosure', 'publication', 'annual', 'quarterly']
        
        for url in urls:
            url_lower = url.lower()
            if any(kw in url_lower for kw in reports_keywords):
                print(f"  Detected reports page URL: {url}")
                return url
        
        # Return first URL even if doesn't have keywords
        return urls[0]
    
    def _extract_from_user_url(self, prompt: str, reports_url: str) -> Dict:
        """
        Extract PDFs directly from user-provided reports URL.
        This is the PRIMARY source when user provides a URL.
        """
        print(f"\n[DIRECT EXTRACTION] Fetching page: {reports_url}")
        
        # Parse the original prompt for company and years
        parsed = self._parse_query(prompt)
        company = parsed.get('company', 'Unknown Company')
        requested_years = parsed.get('years', [datetime.now().year])
        report_type = parsed.get('report_type', 'annual')
        
        # Extract official website from URL
        parsed_url = urlparse(reports_url)
        official_website = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        reports = []
        notes_list = []
        
        try:
            # Fetch the page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = requests.get(reports_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            html_content = response.text
            print(f"  Page fetched: {len(html_content)} bytes")
            
            # Extract all PDF links from the page
            pdf_links = self._extract_pdfs_from_html(html_content, reports_url)
            print(f"  Found {len(pdf_links)} PDF links")
            
            # Filter and categorize PDFs
            for pdf in pdf_links:
                pdf_url = pdf['url']
                title = pdf['title']
                
                # Try to extract year from title or URL
                year_match = re.search(r'(20\d{2})', title + pdf_url)
                pdf_year = int(year_match.group(1)) if year_match else None
                
                # If we have specific years requested, filter
                if requested_years and pdf_year and pdf_year not in requested_years:
                    continue
                
                # Detect document type from title
                title_lower = title.lower()
                if 'annual' in title_lower or 'yearly' in title_lower:
                    doc_type = 'annual_report'
                elif 'quarterly' in title_lower or any(q in title_lower for q in ['q1', 'q2', 'q3', 'q4']):
                    doc_type = 'quarterly_report'
                elif 'interim' in title_lower or 'half' in title_lower:
                    doc_type = 'interim_report'
                else:
                    doc_type = report_type
                
                reports.append({
                    'year': pdf_year or datetime.now().year,
                    'type': doc_type,
                    'title': title,
                    'url': pdf_url,
                    'source_page': reports_url,
                    'source': 'direct_extraction'
                })
            
            if not reports:
                notes_list.append(f"Fetched {reports_url} but found no matching PDF links")
                notes_list.append("Page may use JavaScript rendering or dynamic loading")
            else:
                notes_list.append(f"Extracted {len(reports)} PDFs from {reports_url}")
            
        except requests.RequestException as e:
            notes_list.append(f"Failed to fetch page: {str(e)}")
            print(f"  Error fetching page: {e}")
        except Exception as e:
            notes_list.append(f"Extraction error: {str(e)}")
            print(f"  Extraction error: {e}")
        
        # Calculate missing years
        found_years = set(r.get('year') for r in reports)
        missing_years = sorted([y for y in requested_years if y not in found_years])
        
        notes = ". ".join(notes_list) if notes_list else "Extraction completed"
        
        print(f"\n[OK] Extracted {len(reports)} reports from user-provided URL")
        
        return {
            'company': company,
            'official_website': official_website,
            'official_investor_relations': '',
            'reports_pages': [{'doc_category': 'Reports', 'url': reports_url}],
            'reports': reports,
            'missing_years': missing_years,
            'requested_years': list(requested_years),
            'notes': notes
        }
    
    def _extract_pdfs_from_html(self, html: str, base_url: str) -> List[Dict]:
        """
        Extract PDF links from HTML content.
        Handles relative URLs and various link patterns.
        """
        from urllib.parse import urljoin
        
        pdf_links = []
        seen_urls = set()
        
        # Pattern 1: Direct PDF links in href
        href_pattern = r'<a[^>]+href=["\']([^"\']+\.pdf[^"\']*)["\'][^>]*>([^<]*)</a>'
        for match in re.finditer(href_pattern, html, re.IGNORECASE):
            url = match.group(1)
            title = match.group(2).strip() or "Untitled PDF"
            
            # Handle relative URLs
            if not url.startswith('http'):
                url = urljoin(base_url, url)
            
            if url not in seen_urls:
                seen_urls.add(url)
                pdf_links.append({'url': url, 'title': title})
        
        # Pattern 2: Links with .pdf anywhere in href (may have query params)
        href_pattern2 = r'<a[^>]+href=["\']([^"\']*["\']?)[^>]*>([^<]*)</a>'
        for match in re.finditer(href_pattern2, html, re.IGNORECASE):
            url = match.group(1).rstrip('"\'')
            title = match.group(2).strip()
            
            if '.pdf' in url.lower():
                if not url.startswith('http'):
                    url = urljoin(base_url, url)
                
                if url not in seen_urls:
                    seen_urls.add(url)
                    pdf_links.append({'url': url, 'title': title or "PDF Document"})
        
        # Pattern 3: Data attributes that may contain PDF URLs
        data_pattern = r'data-[a-z-]+=["\']([^"\']*\.pdf[^"\']*)["\']'
        for match in re.finditer(data_pattern, html, re.IGNORECASE):
            url = match.group(1)
            if not url.startswith('http'):
                url = urljoin(base_url, url)
            
            if url not in seen_urls:
                seen_urls.add(url)
                pdf_links.append({'url': url, 'title': 'PDF from data attribute'})
        
        # Pattern 4: JavaScript strings containing PDF URLs
        js_pattern = r'["\']([^"\']*\.pdf[^"\']*)["\']'
        for match in re.finditer(js_pattern, html, re.IGNORECASE):
            url = match.group(1)
            if url.startswith('/') or url.startswith('http'):
                if not url.startswith('http'):
                    url = urljoin(base_url, url)
                
                if url not in seen_urls and len(url) < 500:  # Avoid garbage
                    seen_urls.add(url)
                    pdf_links.append({'url': url, 'title': 'PDF from script'})
        
        return pdf_links
    
    def _find_reports_pages(self, company: str, official_website: str) -> List[Dict]:
        """
        Search for official reports listing pages using multiple categories.
        Returns list of {doc_category, url} dicts.
        """
        reports_pages = []
        
        # Categories to search for
        categories = [
            ('Annual', 'annual reports financial statements'),
            ('Quarterly', 'quarterly reports interim results'),
            ('Filings', 'filings disclosures regulatory'),
        ]
        
        for doc_category, keywords in categories:
            query = f'"{company}" {keywords} investor relations page'
            
            try:
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers={
                        'X-API-KEY': self.serper_key,
                        'Content-Type': 'application/json'
                    },
                    json={'q': query, 'num': 5},
                    timeout=5
                )
                
                if response.status_code == 200:
                    results = response.json()
                    
                    # Look for pages with report-like URLs
                    for result in results.get('organic', []):
                        url = result.get('link', '')
                        title = result.get('title', '').lower()
                        
                        # Check if URL contains report-related paths
                        report_paths = ['report', 'result', 'financial', 'publication', 'filing', 'disclosure', 'annual', 'quarterly']
                        if any(path in url.lower() for path in report_paths):
                            # Avoid adding duplicates
                            if not any(rp['url'] == url for rp in reports_pages):
                                reports_pages.append({
                                    'doc_category': doc_category,
                                    'url': url
                                })
                                break  # Only add first match per category
                
            except Exception as e:
                print(f"    Error searching for {doc_category} pages: {e}")
        
        return reports_pages
    
    def _search_site_restricted(self, site_domain: str, company: str, report_type: str, year: int) -> List[Dict]:
        """
        Perform site-restricted Google search for reports on official domain.
        """
        queries = [
            f'site:{site_domain} annual report {year} filetype:pdf',
            f'site:{site_domain} financial statements {year} pdf',
            f'site:{site_domain} results reports archive {year} pdf',
        ]
        
        all_results = []
        
        for query in queries:
            print(f"    → Site search: {query}")
            
            try:
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers={
                        'X-API-KEY': self.serper_key,
                        'Content-Type': 'application/json'
                    },
                    json={'q': query, 'num': 5},
                    timeout=5
                )
                
                if response.status_code == 200:
                    results = response.json()
                    pdf_results = self._extract_pdf_urls(results, year, report_type, company)
                    if pdf_results:
                        all_results.extend(pdf_results)
                        break  # Stop if we found results
                
            except Exception as e:
                print(f"    Error in site search: {e}")
        
        return all_results
    
    def _parse_query(self, prompt: str) -> Dict:
        """Parse query using OpenAI or fallback to regex."""
        # Try OpenAI first
        if self.openai_client:
            try:
                return self._parse_with_openai(prompt)
            except Exception as e:
                print(f"OpenAI parsing failed: {e}, using fallback")
        
        # Fallback to regex
        return self._parse_with_regex(prompt)
    
    def _parse_with_openai(self, prompt: str) -> Dict:
        """Parse query using OpenAI for smart understanding."""
        system_prompt = """Parse the user's query to extract:
1. Company name (full name or ticker)
2. Report type (annual, quarterly, 10-K, 10-Q, earnings, financial_statements)
3. Years (expand ranges like "2020 to 2024" to [2020, 2021, 2022, 2023, 2024])
4. Specific quarters if mentioned (Q1, Q2, Q3, Q4 or ranges like Q1-Q4)

Respond in JSON:
{
  "company": "company name or ticker",
  "report_type": "annual|quarterly|10-k|10-q|earnings|financial_statements",
  "years": [2020, 2021, 2022],
  "quarters": ["Q1", "Q2", "Q3", "Q4"]  // Only if specific quarters requested, otherwise null
}

IMPORTANT:
- If user says "Q1 2023" -> quarters: ["Q1"], years: [2023]
- If user says "Q1-Q4 2023" -> quarters: ["Q1", "Q2", "Q3", "Q4"], years: [2023]
- If user just says "quarterly 2023" -> quarters: null (accept any quarter)
- If no years specified, use current year. If no report type, use "annual"."""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"},
            timeout=5  # Reduced timeout for faster responses
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _parse_with_regex(self, prompt: str) -> Dict:
        """Fallback parser using regex patterns with STRICT quarter handling."""
        prompt_lower = prompt.lower()
        
        # ========== STEP 1: EXTRACT SPECIFIC QUARTERS ==========
        # Pattern: "Q4 2023", "Q1 2023", "Q1-Q4 2023"
        quarters = []
        quarter_year_pairs = []  # List of (quarter, year) tuples
        
        # Ordinal to Q mapping
        ordinal_map = {'first': 'Q1', 'second': 'Q2', 'third': 'Q3', 'fourth': 'Q4'}
        
        # Pattern 1: "Q4 2023", "Q1-Q4 2023"
        q_range_match = re.search(r'Q([1-4])\s*[-–]\s*Q([1-4])\s*(\d{4})?', prompt, re.IGNORECASE)
        if q_range_match:
            start_q = int(q_range_match.group(1))
            end_q = int(q_range_match.group(2))
            year = int(q_range_match.group(3)) if q_range_match.group(3) else None
            for q in range(start_q, end_q + 1):
                quarters.append(f'Q{q}')
                if year:
                    quarter_year_pairs.append((f'Q{q}', year))
        else:
            # Pattern 2: Single quarter "Q4 2023"
            q_matches = re.findall(r'Q([1-4])\s*(\d{4})?', prompt, re.IGNORECASE)
            for q, year in q_matches:
                quarters.append(f'Q{q}')
                if year:
                    quarter_year_pairs.append((f'Q{q}', int(year)))
        
        # Pattern 3: "Fourth Quarter 2023", "First Quarter 2023"
        ordinal_matches = re.findall(r'(first|second|third|fourth)\s+quarter\s*(\d{4})?', prompt_lower)
        for ordinal, year in ordinal_matches:
            q = ordinal_map.get(ordinal)
            if q and q not in quarters:
                quarters.append(q)
                if year:
                    quarter_year_pairs.append((q, int(year)))
        
        # Remove duplicates while preserving order
        quarters = list(dict.fromkeys(quarters))
        
        # ========== STEP 2: EXTRACT YEARS ==========
        years = []
        year_match = re.search(r'(\d{4})\s*(?:to|-)\s*(\d{4})', prompt)
        if year_match:
            start_year = int(year_match.group(1))
            end_year = int(year_match.group(2))
            years = list(range(start_year, end_year + 1))
        else:
            years = [int(y) for y in re.findall(r'\b(20\d{2})\b', prompt)]
        
        if not years:
            years = [datetime.now().year]
        
        # If we have quarter-year pairs but no years extracted, use years from pairs
        if quarter_year_pairs and not years:
            years = list(set(y for _, y in quarter_year_pairs))
        
        # ========== STEP 3: DETERMINE REPORT TYPE ==========
        # CRITICAL: If specific quarters detected, set report_type to 'quarterly'
        # and mark that we have specific quarters
        report_type = 'annual'
        
        if quarters:
            report_type = 'quarterly'  # Specific quarters requested
        elif 'quarterly' in prompt_lower or 'quarter' in prompt_lower:
            report_type = 'quarterly'  # Generic quarterly request
        elif '10-k' in prompt_lower:
            report_type = '10-k'
        elif '10-q' in prompt_lower:
            report_type = 'quarterly'  # 10-Q is quarterly
            quarters = ['Q1', 'Q2', 'Q3', 'Q4']  # All quarters
        elif 'earnings' in prompt_lower:
            report_type = 'earnings'
        elif 'financial' in prompt_lower:
            report_type = 'financial_statements'
        
        # Extract company name (improved to handle Unicode and tickers)
        # Pattern 1: "... of/for <COMPANY> ..." or "... of/for <COMPANY> (<TICKER>) ..."
        # Use \w+ to match Unicode letters and underscores
        of_match = re.search(
            r'(?:of|for)\s+([\w\s\.\-\(\)]+?)(?:\s+(?:from|for|year|20\d{2}|annual|quarterly|financial|statement)|\s*$)', 
            prompt, 
            re.IGNORECASE | re.UNICODE
        )
        
        if of_match:
            company = of_match.group(1).strip()
        else:
            # Pattern 2: Extract everything before report type keywords
            parts = re.split(
                r'\b(annual|quarterly|10-k|10-q|earnings|report|from|for|year|financial|statement)\b', 
                prompt, 
                flags=re.IGNORECASE
            )
            company = parts[0].strip()
        
        # Clean up company name
        company = re.sub(r'\s+', ' ', company).strip()
        
        # Validate we actually found a company
        if not company or len(company) < 2:
            # Last resort: take first capitalized words
            words = prompt.split()
            company_words = []
            for word in words:
                if word[0].isupper() or '(' in word:  # Capital letter or ticker
                    company_words.append(word)
                elif company_words and len(company_words) < 5:  # Continue for a few words
                    company_words.append(word)
                elif company_words:  # Stop after collecting some words
                    break
            company = ' '.join(company_words) if company_words else None
        
        return {
            'company': company,
            'report_type': report_type,
            'years': years,
            'quarters': quarters,  # Specific quarters requested (e.g., ['Q4'] or ['Q1', 'Q2', 'Q3', 'Q4'])
            'quarter_year_pairs': quarter_year_pairs  # List of (quarter, year) tuples for exact period matching
        }
    
    def _search_with_serper(self, company: str, report_type: str, years: List[int], requested_quarters: List[str] = None) -> List[Dict]:
        """
        Search for reports using Serper API with parallel processing.
        
        KEY RULE for ANNUAL: Returns EXACTLY ONE PDF per year (best scored) or none.
        KEY RULE for QUARTERLY: Returns EXACTLY ONE PDF per (year, quarter) pair.
        requested_quarters: If specified (e.g. ['Q1']), only return docs for those specific quarters.
        """
        print(f"\n⏳ Searching {len(years)} years...")
        if requested_quarters:
            print(f"  ➡️ Looking for specific quarters: {requested_quarters}")
        all_candidates = []
        
        # For quarterly requests with specific quarters, search for each (year, quarter) pair
        if report_type == 'quarterly' and requested_quarters:
            # Create list of (year, quarter) pairs to search
            search_periods = [(year, q) for year in years for q in requested_quarters]
            print(f"  📅 Searching {len(search_periods)} period(s): {search_periods}")
            
            # Process periods in parallel (max 4 concurrent)
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_period = {
                    executor.submit(self._search_quarter, company, year, quarter): (year, quarter) 
                    for year, quarter in search_periods
                }
                
                for future in as_completed(future_to_period):
                    year, quarter = future_to_period[future]
                    try:
                        period_candidates = future.result(timeout=10)
                        if period_candidates:
                            all_candidates.extend(period_candidates)
                            print(f"  ✓ {quarter} {year}: Found {len(period_candidates)} candidates")
                        else:
                            print(f"  - {quarter} {year}: No candidates found")
                    except Exception as e:
                        print(f"  ✗ {quarter} {year}: Error - {e}")
        else:
            # Process years in parallel (max 3 concurrent) for annual/generic requests
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_year = {
                    executor.submit(self._search_year, company, report_type, year, requested_quarters): year 
                    for year in years
                }
                
                for future in as_completed(future_to_year):
                    year = future_to_year[future]
                    try:
                        year_candidates = future.result(timeout=8)
                        if year_candidates:
                            all_candidates.extend(year_candidates)
                            print(f"  ✓ Year {year}: Found {len(year_candidates)} candidates")
                        else:
                            print(f"  - Year {year}: No candidates found")
                    except Exception as e:
                        print(f"  ✗ Year {year}: Error - {e}")
        
        # ========== SELECTION LOGIC ==========
        best_reports = []
        
        if report_type == 'quarterly' and requested_quarters:
            # QUARTERLY MODE: Select ONE BEST PDF per (year, quarter) pair
            print(f"\n📊 Selecting best PDF per period from {len(all_candidates)} candidates...")
            
            # Group candidates by (year, quarter)
            candidates_by_period = {}
            for candidate in all_candidates:
                year = candidate.get('reporting_period_year', candidate.get('year'))
                quarter = candidate.get('quarter')  # Should be set by _extract_pdf_urls
                if year and quarter:
                    period_key = (year, quarter)
                    if period_key not in candidates_by_period:
                        candidates_by_period[period_key] = []
                    candidates_by_period[period_key].append(candidate)
            
            # Select best candidate for each requested (year, quarter)
            for year in years:
                for quarter in requested_quarters:
                    period_key = (year, quarter.upper())
                    if period_key in candidates_by_period:
                        period_candidates = candidates_by_period[period_key]
                        scored = [(self._score_document(c, company), c) for c in period_candidates]
                        scored.sort(reverse=True, key=lambda x: x[0])
                        
                        best_score, best_doc = scored[0]
                        if best_score > 0:
                            best_doc['score'] = best_score
                            best_reports.append(best_doc)
                            print(f"  [BEST] {quarter} {year}: {best_doc['title'][:50]}... (score: {best_score})")
                        else:
                            print(f"  [NONE] {quarter} {year}: All candidates rejected (best score: {best_score})")
                    else:
                        print(f"  [MISS] {quarter} {year}: No candidates found")
        else:
            # ANNUAL MODE: Select ONE BEST PDF per year
            print(f"\n📊 Selecting best PDF per year from {len(all_candidates)} candidates...")
            
            # Group candidates by reporting_period_year
            candidates_by_year = {}
            for candidate in all_candidates:
                year = candidate.get('reporting_period_year', candidate.get('year'))
                if year not in candidates_by_year:
                    candidates_by_year[year] = []
                candidates_by_year[year].append(candidate)
            
            # Select best candidate for each year
            for year in years:
                if year in candidates_by_year:
                    year_candidates = candidates_by_year[year]
                    scored = [(self._score_document(c, company), c) for c in year_candidates]
                    scored.sort(reverse=True, key=lambda x: x[0])
                    
                    best_score, best_doc = scored[0]
                    if best_score > 0:
                        best_doc['score'] = best_score
                        best_reports.append(best_doc)
                        print(f"  [BEST] Year {year}: {best_doc['title'][:50]}... (score: {best_score})")
                    else:
                        print(f"  [NONE] Year {year}: All candidates rejected (best score: {best_score})")
                else:
                    print(f"  [MISS] Year {year}: No candidates found")
        
        return best_reports
    
    def _score_document(self, doc: Dict, company: str) -> int:
        """
        Score a document for selection. Higher = better.
        
        SOURCE PRIORITY (CRITICAL):
        +100 if PDF is from verified company domain (e.g., naspers.com)
        +50 if title includes "Annual Report" + year
        +30 if URL path includes /investor/ /ir/ /reports/ /annual/
        -50 if PDF is from exchange/regulator (HKEX, SEC) when user asked for "annual report"
        -1000 if excluded type (ESG, integrated, etc.)
        """
        title_lower = doc.get('title', '').lower()
        url_lower = doc.get('url', '').lower()
        score = 0
        
        # ========== SOURCE PRIORITY (MOST IMPORTANT) ==========
        # Check if URL is from company's own domain
        significant_words = self._get_significant_words(company)
        domain = urlparse(doc.get('url', '')).netloc.lower()
        
        is_company_domain = any(word in domain for word in significant_words)
        is_exchange_domain = any(ex in domain for ex in [
            'hkex', 'hkexnews', 'sec.gov', 'edgar', 'jse.co.za', 
            'londonstockexchange', 'lse.co.uk', 'bse', 'nse'
        ])
        
        if is_company_domain:
            score += 100  # STRONGLY prefer company IR PDFs
            print(f"    +100 (company domain)")
        elif is_exchange_domain:
            score -= 50  # Penalize exchange filings for "annual report" requests
            print(f"    -50 (exchange/regulator domain)")
        
        # ========== CONTENT SCORING ==========
        # Prefer "Annual Report" in title (multiple languages)
        annual_keywords = [
            'annual report', 'informe anual',  # English, Spanish
            'rapport annuel',  # French
            'geschäftsbericht', 'jahresbericht',  # German
            'faaliyet raporu', 'yıllık rapor',  # Turkish
            'relatório anual',  # Portuguese
            'relazione annuale',  # Italian
            'годовой отчет',  # Russian
            'jaarverslag',  # Dutch
            '年次報告', '年度报告',  # Japanese, Chinese
        ]
        if any(kw in title_lower for kw in annual_keywords):
            score += 50
        
        # Prefer consolidated financial statements
        if 'consolidated financial statements' in title_lower:
            score += 40
        elif 'consolidated' in title_lower:
            score += 20
        
        # Prefer IR archive paths (multiple languages)
        ir_paths = [
            '/investor', '/ir/', '/reports/', '/annual/', '/results/',
            '/informes/', '/downloads/', '/rapports/', '/berichte/',
            '/raporlar/', '/relatorios/', '/rapporti/'
        ]
        if any(path in url_lower for path in ir_paths):
            score += 30
        
        # ========== EXCLUSION PENALTIES ==========
        exclude_keywords = [
            'sustainability', 'esg', 'integrated report', 'annual review',
            'presentation', 'highlights', 'summary', 'activity report',
            'independent auditor', 'proxy', 'circular', 'notice'
        ]
        for kw in exclude_keywords:
            if kw in title_lower:
                score -= 1000
                break
        
        return score
    
    def _search_quarter(self, company: str, year: int, quarter: str) -> List[Dict]:
        """
        Search for reports for a single (year, quarter) using targeted queries.
        
        This method is designed to be called in parallel by ThreadPoolExecutor.
        Returns candidates with the 'quarter' field already set.
        """
        all_candidates = []
        quarter_upper = quarter.upper()
        
        # Quarter-specific labels for search
        quarter_labels = {
            'Q1': ['Q1', '1Q', 'First Quarter', 'first quarter'],
            'Q2': ['Q2', '2Q', 'Second Quarter', 'second quarter'],
            'Q3': ['Q3', '3Q', 'Third Quarter', 'third quarter'],
            'Q4': ['Q4', '4Q', 'Fourth Quarter', 'fourth quarter']
        }
        labels = quarter_labels.get(quarter_upper, [quarter])
        
        # Generate targeted queries for this specific quarter (limited for speed)
        queries = [
            f'"{company}" "{labels[0]} {year}" results pdf',
            f'"{company}" "{labels[0]} {year}" financial results filetype:pdf',
        ]
        
        # Try each query strategy (limit to 2 for speed)
        for query in queries[:2]:
            print(f"    → Searching: {query}")
            
            try:
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers={
                        'X-API-KEY': self.serper_key,
                        'Content-Type': 'application/json'
                    },
                    json={
                        'q': query,
                        'num': 10
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    results = response.json()
                    # Extract with the specific quarter filter
                    candidates = self._extract_pdf_urls(
                        results, year, 'quarterly', company, [quarter_upper]
                    )
                    if candidates:
                        # VERIFY: Only keep candidates that actually match the requested quarter
                        # Do NOT forcefully override the quarter - trust the extraction
                        verified_candidates = []
                        for c in candidates:
                            extracted_quarter = c.get('quarter')
                            if extracted_quarter == quarter_upper:
                                verified_candidates.append(c)
                            else:
                                print(f"    [FILTER] Rejected {c.get('title', '')[:40]}... (extracted {extracted_quarter}, need {quarter_upper})")
                        
                        if verified_candidates:
                            all_candidates.extend(verified_candidates)
                            # If we found good results, stop searching
                            if len(verified_candidates) >= 1:
                                break
                else:
                    print(f"      [ERROR] Serper returned status {response.status_code}")
            
            except Exception as e:
                print(f"      Serper search error: {e}")
        
        return all_candidates
    
    def _search_year(self, company: str, report_type: str, year: int, requested_quarters: List[str] = None) -> List[Dict]:
        """
        Search for reports for a single year using multiple query strategies.
        
        This method is designed to be called in parallel by ThreadPoolExecutor.
        requested_quarters: If specified (e.g. ['Q1']), only return docs for those specific quarters.
        """
        all_candidates = []
        
        # Get clean company name for site search
        company_clean = company.lower().replace('pjsc', '').replace('oil company', '').strip()
        company_first_word = company_clean.split()[0] if company_clean.split() else company_clean
        
        # Multiple search strategies for better recall
        if report_type in ['annual', '10-k', 'financial_statements']:
            queries = [
                # Strategy 1: Simple annual report search (broadest)
                f'"{company}" annual report {year} filetype:pdf',
                # Strategy 2: Investor relations specific
                f'"{company}" investor relations annual report {year} pdf',
                # Strategy 3: Spanish - informe anual
                f'"{company}" informe anual {year} filetype:pdf',
                # Strategy 4: French - rapport annuel
                f'"{company}" rapport annuel {year} filetype:pdf',
                # Strategy 5: German - Geschäftsbericht / Jahresbericht
                f'"{company}" Geschäftsbericht {year} filetype:pdf',
                # Strategy 6: Portuguese - relatório anual
                f'"{company}" relatório anual {year} filetype:pdf',
                # Strategy 7: Turkish - yıllık rapor / faaliyet raporu
                f'"{company}" faaliyet raporu {year} filetype:pdf',
                # Strategy 8: Russian - годовой отчет
                f'"{company}" годовой отчет {year} filetype:pdf',
                # Strategy 9: Site-specific search
                f'site:{company_first_word}.com annual report {year} pdf',
            ]
            # IMPROVED: Use 5 queries for better recall  
            queries = queries[:5]
        elif report_type == 'quarterly':
            # ========== QUARTER-SPECIFIC SEARCH QUERIES ==========
            # If specific quarters requested, generate targeted queries
            if requested_quarters:
                queries = []
                quarter_labels = {
                    'Q1': ['Q1', '1Q', 'First Quarter', 'first quarter'],
                    'Q2': ['Q2', '2Q', 'Second Quarter', 'second quarter'],
                    'Q3': ['Q3', '3Q', 'Third Quarter', 'third quarter'],
                    'Q4': ['Q4', '4Q', 'Fourth Quarter', 'fourth quarter']
                }
                for q in requested_quarters:
                    labels = quarter_labels.get(q.upper(), [q])
                    # Primary query with exact quarter label
                    queries.append(f'"{company}" "{labels[0]} {year}" results pdf')
                    queries.append(f'"{company}" "{labels[0]} {year}" earnings pdf')
                    # Secondary query with alternate label
                    if len(labels) > 1:
                        queries.append(f'"{company}" "{labels[1]} {year}" financial results pdf')
                    # Ordinal quarter query
                    if len(labels) > 2:
                        queries.append(f'"{company}" "{labels[2]} {year}" pdf')
            else:
                # Generic quarterly request - search for any quarter
                queries = [
                    f'"{company}" quarterly report {year} filetype:pdf',
                    f'"{company}" Q1 Q2 Q3 Q4 {year} results pdf',
                    f'"{company}" interim report {year} filetype:pdf',
                ]
        elif report_type == 'earnings':
            queries = [
                f'"{company}" earnings release {year} filetype:pdf',
                f'"{company}" earnings report {year} filetype:pdf',
                f'"{company}" press release results {year} filetype:pdf',
            ]
        elif report_type == 'presentation':
            queries = [
                f'"{company}" investor presentation {year} filetype:pdf',
                f'"{company}" earnings presentation {year} filetype:pdf',
            ]
        elif report_type in ['10-k', '10-q', 'sec']:
            queries = [
                f'"{company}" 10-K {year} filetype:pdf',
                f'"{company}" 10-Q {year} filetype:pdf',
                f'site:sec.gov "{company}" 10-K {year}',
            ]
        else:
            queries = [
                f'"{company}" {report_type} report {year} filetype:pdf',
            ]
        
        # Try each query strategy
        for query in queries:
            print(f"  → Searching: {query}")
            
            try:
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers={
                        'X-API-KEY': self.serper_key,
                        'Content-Type': 'application/json'
                    },
                    json={
                        'q': query,
                        'num': 10
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    results = response.json()
                    candidates = self._extract_pdf_urls(results, year, report_type, company, requested_quarters)
                    if candidates:
                        all_candidates.extend(candidates)
                        # If we found good results, stop searching
                        if len(candidates) >= 2:
                            break
                else:
                    print(f"    [ERROR] Serper returned status {response.status_code}: {response.text}")
            
            except Exception as e:
                print(f"    Serper search error: {e}")
        
        return all_candidates
    
    def _deduplicate_reports(self, reports: List[Dict]) -> List[Dict]:
        """
        Remove duplicate reports by URL.
        """
        seen_urls = set()
        unique_reports = []
        
        for report in reports:
            if report['url'] not in seen_urls:
                seen_urls.add(report['url'])
                unique_reports.append(report)
        
        return unique_reports
    
    def _extract_reporting_period_year(self, title: str, url: str, snippet: str, search_year: int) -> int:
        """
        Extract the document's actual reporting period year from title, URL, and snippet.
        
        Priority: title > URL > snippet
        Falls back to search_year if no year can be confidently extracted.
        
        Args:
            title: Document title from search result
            url: PDF URL
            snippet: Search result snippet
            search_year: The year we searched for (fallback)
        
        Returns:
            The extracted reporting period year (fiscal year)
        """
        # Patterns to match fiscal/reporting year (in priority order)
        patterns = [
            # "Annual Report 2020", "2020 Annual Report"
            r'annual\s+report\s+(\d{4})',
            r'(\d{4})\s+annual\s+report',
            # "FY2020", "FY 2020", "Fiscal Year 2020"
            r'fy\s*(\d{4})',
            r'fiscal\s+year\s+(\d{4})',
            # "For the year ended 31 December 2020", "Year ended 2020"
            r'(?:for\s+)?(?:the\s+)?year\s+ended\s+(?:\d+\s+\w+\s+)?(\d{4})',
            # "10-K 2020", "Form 10-K 2020", "2020 10-K"
            r'10-k\s+(\d{4})',
            r'(\d{4})\s+(?:form\s+)?10-k',
            r'form\s+10-k\s+(\d{4})',
            # "20-F 2020", "Form 20-F 2020"
            r'20-f\s+(\d{4})',
            r'(\d{4})\s+(?:form\s+)?20-f',
            # "Results 2020", "FY20 Results"
            r'results?\s+(\d{4})',
            r'fy(\d{2})\s+results?',  # FY20 -> 2020
            # URL patterns like /2020/, _2020_, -2020-
            r'/(\d{4})/',
            r'[_-](\d{4})[_.-]',
            r'(\d{4})\.pdf$',
        ]
        
        combined_text = f"{title} {url} {snippet}".lower()
        
        # Try each pattern
        for pattern in patterns:
            match = re.search(pattern, combined_text)
            if match:
                year_str = match.group(1)
                # Handle 2-digit years (FY20 -> 2020)
                if len(year_str) == 2:
                    year = 2000 + int(year_str)
                else:
                    year = int(year_str)
                
                # Validate year is reasonable (2000-2030)
                if 2000 <= year <= 2030:
                    return year
        
        # Fallback to search year if no year found
        return search_year
    
    def _extract_company_domain(self, company: str) -> str:
        """Extract likely company domain for site-specific search."""
        # Clean company name and create domain guess
        clean_name = re.sub(r'[^\w\s]', '', company.lower())
        clean_name = clean_name.split()[0] if clean_name.split() else company.lower()
        return f"{clean_name}.com OR {clean_name}.ru OR {clean_name}.co.uk"

    
    def _extract_pdf_urls(self, serper_results: Dict, year: int, report_type: str, company: str, requested_quarters: List[str] = None) -> List[Dict]:
        """
        Extract PDF URLs from Serper search results with STRICT filtering.
        
        CRITICAL: Only returns documents where:
        1. Extracted reporting_period_year == requested year (EXACT MATCH)
        2. Document type matches request (annual, quarterly, financial statements)
        3. No excluded keywords (sustainability, ESG, etc.)
        4. If requested_quarters specified, document must match EXACT quarter (Q1/Q2/Q3/Q4)
        """
        pdf_reports = []
        
        # Quarter mapping for exact matching
        quarter_map = {
            'Q1': ['q1', '1q', 'first quarter', 'march', 'jan-mar', 'jan - mar'],
            'Q2': ['q2', '2q', 'second quarter', 'june', 'apr-jun', 'apr - jun', 'h1', 'half year', '6 month', '6m'],
            'Q3': ['q3', '3q', 'third quarter', 'september', 'jul-sep', 'jul - sep', '9m', '9 month', 'nine month'],
            'Q4': ['q4', '4q', 'fourth quarter', 'december', 'oct-dec', 'oct - dec', 'h2']
        }
        
        # Document type keywords (whitelist)
        quarterly_keywords = [
            'q1', 'q2', 'q3', 'q4', 'quarter', 'quarterly', '1q', '2q', '3q', '4q',
            'interim', 'half', 'h1', 'h2', '6m', '9m', 'nine month', 'six month', 'trading update'
        ]
        
        # Financial statement keywords (for annual/financial_statements requests)
        financial_statement_keywords = [
            'financial statements', 'annual financial statements', 'audited financial',
            'consolidated financial statements', 'ifrs financial', 'annual accounts',
            'statement of financial position', 'income statement', 'cash flow statement',
            '10-k', 'form 10-k', '20-f', 'form 20-f', 'annual report'
        ]
        
        # Strong accept (high confidence financial documents)
        strong_accept_keywords = [
            'consolidated financial statements', 'audited financial statements',
            'independent auditor', 'statement of comprehensive income',
            'statement of financial position', 'annual accounts'
        ]
        
        # STRICT exclusion list - ONLY reject documents where the TITLE indicates wrong type
        # NOTE: We check title+URL only, NOT snippet - snippets often mention topics covered BY the report
        exclude_keywords = [
            # Sustainability-only documents (when title is ONLY about sustainability)
            'sustainability report', 'esg report', 'environmental report',
            'climate report', 'carbon report',
            # Activity/Non-financial reports
            'activity report', 'integrated report',
            'corporate governance report',  # Full phrase, not just 'corporate governance'
            # Prospectus/Bond documents (NOT annual reports)
            'prospectus', 'base prospectus', 'bond offering',
            'offering circular', 'offering memorandum',
            # Academic
            'thesis', 'dissertation',
            # Investment banks/trusts/third-party (NOT company's own reports)
            'form n-q', 'form n-csr',
            'investment trust', 'fund prospectus', 'fund report',
        ]
        
        # Earnings release keywords (for earnings report_type)
        earnings_keywords = [
            'earnings', 'earnings release', 'earnings report', 'results announcement',
            'press release', 'results', 'trading update', 'quarterly results',
            'financial results', 'comunicado', 'communiqué', 'ergebnis'
        ]
        
        # Presentation keywords
        presentation_keywords = [
            'presentation', 'investor presentation', 'earnings presentation',
            'results presentation', 'investor day', 'earnings deck', 'slides'
        ]
        
        # Check organic results
        for result in serper_results.get('organic', []):
            link = result.get('link', '')
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()
            original_title = result.get('title', '')
            combined_text = title + ' ' + snippet + ' ' + link.lower()
            
            # Check if it's a PDF link
            if '.pdf' not in link.lower() and 'pdf' not in title:
                continue
            
            if not self._validate_pdf_url(link):
                continue
            
            # ========== STEP 0: CRITICAL COMPANY DOMAIN VALIDATION ==========
            # PDF URL domain MUST belong to the requested company
            # Rejects PDFs from related but different companies (e.g., Prosus when Naspers requested)
            if not self._validate_company_domain(link, company):
                domain = urlparse(link).netloc
                print(f"  [X] REJECTED (WRONG COMPANY DOMAIN '{domain}'): {original_title[:50]}")
                continue
            
            # ========== STEP 1: STRICT EXCLUSION CHECK ==========
            # IMPORTANT: Only check title and link for exclusion keywords, NOT snippet
            # Snippets often mention topics covered BY the report (e.g., sustainability section in annual report)
            title_and_link = title + ' ' + link.lower()
            is_excluded = any(kw in title_and_link for kw in exclude_keywords)
            if is_excluded:
                excluded_kw = [kw for kw in exclude_keywords if kw in title_and_link][0]
                print(f"  [X] REJECTED (excluded keyword '{excluded_kw}'): {original_title[:50]}")
                continue
            
            # ========== STEP 2: ACADEMIC SOURCE CHECK ==========
            is_academic = any(domain in link.lower() for domain in [
                'researchgate', 'academia.edu', 'ssrn', 'jstor', 'springer',
                'sciencedirect', 'wiley', 'tandfonline', 'emerald'
            ])
            if is_academic:
                print(f"  [X] REJECTED (academic source): {original_title[:50]}")
                continue
            
            # ========== STEP 3: DOCUMENT TYPE VALIDATION ==========
            # ========== EXTRACT DOCUMENT QUARTER ==========
            # For quarterly requests, extract which quarter this document is for
            doc_quarter = None
            if report_type == 'quarterly':
                strict_quarter_patterns = {
                    'Q1': ['q1', '1q', 'first quarter', 'q1 '],
                    'Q2': ['q2', '2q', 'second quarter', 'q2 '],
                    'Q3': ['q3', '3q', 'third quarter', 'q3 '],
                    'Q4': ['q4', '4q', 'fourth quarter', 'q4 ']
                }
                for q, keywords in strict_quarter_patterns.items():
                    if any(kw in combined_text for kw in keywords):
                        doc_quarter = q
                        break
                
                # ========== STRICT REJECT: Annual/Full-Year docs ==========
                quarterly_reject_keywords = [
                    'annual report', 'annual-report', 'annualreport', 'yearly report',
                    'annual financial statements', 'annual accounts', 'annual results',
                    'full year', 'full-year', 'fullyear', 'full year results',
                    'fy results', '12 month results', '12m results',
                    'year ended december', 'year ended 31', 'year ending december',
                    '10-k', 'form 10-k'
                ]
                is_full_year_doc = any(kw in combined_text for kw in quarterly_reject_keywords)
                
                if is_full_year_doc:
                    rejected_kw = [kw for kw in quarterly_reject_keywords if kw in combined_text][0]
                    print(f"  [X] REJECTED (FULL YEAR doc for quarterly request - '{rejected_kw}'): {original_title[:50]}")
                    continue
                
                # ========== EXACT QUARTER MATCHING ==========
                if requested_quarters:
                    normalized_req = [q.upper() for q in requested_quarters]
                    
                    if doc_quarter is None:
                        print(f"  [X] REJECTED (no specific Q1/Q2/Q3/Q4 label, interim/H1/H2 not accepted): {original_title[:50]}")
                        continue
                    
                    if doc_quarter not in normalized_req:
                        print(f"  [X] REJECTED (WRONG QUARTER - found {doc_quarter}, need {normalized_req}): {original_title[:50]}")
                        continue
                else:
                    # Generic quarterly request - accept any quarter label
                    quarter_generic_keywords = [
                        'q1', 'q2', 'q3', 'q4', '1q', '2q', '3q', '4q',
                        'first quarter', 'second quarter', 'third quarter', 'fourth quarter',
                        'h1', 'h2', 'half year', 'half-year', 'interim', '6 month', '9 month'
                    ]
                    has_quarter_label = any(kw in combined_text for kw in quarter_generic_keywords)
                    if not has_quarter_label:
                        print(f"  [X] REJECTED (no quarterly indicator): {original_title[:50]}")
                        continue
            
            elif report_type == 'earnings':
                has_earnings = any(kw in combined_text for kw in earnings_keywords)
                if not has_earnings:
                    print(f"  [X] REJECTED (not earnings release): {original_title[:50]}")
                    continue
            
            elif report_type == 'presentation':
                has_presentation = any(kw in combined_text for kw in presentation_keywords)
                if not has_presentation:
                    print(f"  [X] REJECTED (not presentation): {original_title[:50]}")
                    continue
            
            # ========== STRICT ANNUAL REPORT VALIDATION ==========
            elif report_type in ['annual', '10-k', 'financial_statements']:
                # REJECT: Interim/condensed/quarterly/semi-annual docs for annual requests
                annual_reject_keywords = [
                    'interim', 'condensed', 'half-year', 'half year', 'halfyear',
                    'semi-annual', 'semi annual', 'semiannual',  # Half-yearly reports
                    'h1 ', 'h2 ', ' h1', ' h2',  # H1/H2 reports
                    'q1 ', 'q2 ', 'q3 ', 'q4 ', ' q1', ' q2', ' q3', ' q4',
                    'first quarter', 'second quarter', 'third quarter', 'fourth quarter',
                    '6 month', '9 month', 'six month', 'nine month', '6-month', '9-month',
                    '3 month', '3-month', 'three month',  # Quarterly periods
                    'trading update', 'trading statement'
                ]
                is_wrong_type = any(kw in combined_text for kw in annual_reject_keywords)
                if is_wrong_type:
                    rejected_kw = [kw for kw in annual_reject_keywords if kw in combined_text][0]
                    print(f"  [X] REJECTED (WRONG DOC TYPE - '{rejected_kw}' found): {original_title[:50]}")
                    continue
                
                # ACCEPT: Must have annual report keywords OR be a full-year financial document
                annual_accept_keywords = [
                    # Standard annual report labels
                    'annual report', 'annual financial', 'yearly report',
                    'fy20', 'fy19', 'fy21', 'fy22', 'fy23', 'fy24',  # Fiscal year prefixes
                    'fiscal year', 'year ended', 'year ending',
                    # SEC/International filings
                    '10-k', '20-f', 'form 10-k', 'form 20-f', 'annual accounts',
                    # Financial statements (if not already rejected as interim)
                    'financial statements', 'audited financial', 'consolidated financial',
                    'audited accounts', 'annual audited',
                    # Full year results
                    'full year results', 'full-year results', '12 month results',
                    'twelve month', 'full year report', 'annual results',
                    # Russian/CIS variations
                    'годовой отчет', 'annual review',  # Note: "annual review" for CIS companies
                ]
                has_annual = any(kw in combined_text for kw in annual_accept_keywords)
                if not has_annual:
                    print(f"  [X] REJECTED (no annual keywords): {original_title[:50]}")
                    continue
            
            # ========== STEP 4: MANDATORY COMPANY NAME VERIFICATION ==========
            # This is the CRITICAL check that prevents wrong companies (Visa, Home Depot, etc.)
            company_lower = company.lower()
            # Remove parenthetical content and clean up
            company_main = re.sub(r'\s*\([^)]*\)', '', company_lower).strip()
            # Also handle Turkish/special characters by keeping original + ASCII version
            company_ascii = company_main.encode('ascii', 'ignore').decode('ascii')
            company_words = company_main.split() + company_ascii.split()
            company_words = list(set(company_words))  # Remove duplicates
            
            # Common words to SKIP (generic corporate suffixes)
            # NOTE: Keep industry-specific words like 'gas', 'oil', 'petrol' as they identify the company
            common_words = ['inc', 'corp', 'corporation', 'ltd', 'limited', 'co', 'company', 
                           'the', 'and', 'of', 'international', 'pjsc', 'oao', 'pao',
                           'jsc', 'joint', 'stock', 'national', 'a.s.', 'as', 'a.ş.', 'from', 'for']
            # NOTE: 'holding', 'holdings', 'group' are KEPT - they identify companies like Koç Holding
            # NOTE: 'gas', 'oil', 'petrol', 'energy' are KEPT - they identify companies like KazMunayGas
            significant_words = [word for word in company_words if len(word) >= 2 and word not in common_words]
            
            # ALSO check for compound names (e.g. "KazMunayGas" as one word)
            # Extract the main identifying word from the company name
            main_company_word = None
            for word in company_words:
                if len(word) >= 5 and word not in common_words:
                    main_company_word = word
                    break
            
            # MANDATORY: Must have at least 1 significant word match OR compound name match
            company_matched = False
            if significant_words:
                matches = [word for word in significant_words if word in combined_text]
                
                if len(matches) >= 1:
                    company_matched = True
                    print(f"  [DEBUG] Company words: {significant_words}, Matches: {matches}")
            
            # Fallback: Check if the main compound word appears as substring (e.g., "kazmunaygas" in text)
            if not company_matched and main_company_word:
                if main_company_word in combined_text:
                    company_matched = True
                    print(f"  [DEBUG] Compound name match: '{main_company_word}' found")
            
            if not company_matched:
                print(f"  [X] REJECTED (COMPANY MISMATCH - '{significant_words}' not found in doc): {original_title[:50]}")
                continue
            
            # ========== STEP 5: STRICT YEAR EXTRACTION AND VALIDATION ==========
            # Extract actual reporting period year
            reporting_year = self._extract_reporting_period_year(
                title=title,
                url=link,
                snippet=snippet,
                search_year=year
            )
            
            # CRITICAL: STRICT YEAR MATCH - extracted year MUST equal requested year
            if reporting_year != year:
                print(f"  [X] REJECTED (YEAR MISMATCH: extracted FY{reporting_year}, requested FY{year}): {original_title[:50]}")
                continue
            
            # ========== STEP 6: ACCEPT THE DOCUMENT ==========
            source_page = result.get('displayLink', '')
            if source_page:
                source_page = f"https://{source_page}"
            
            # Build period string for quarterly requests
            period = f"FY{reporting_year}"
            if doc_quarter:
                period = f"{doc_quarter} {reporting_year}"
                print(f"  [✓] ACCEPTED: {original_title[:60]} ({period})")
            else:
                print(f"  [✓] ACCEPTED: {original_title[:60]} (FY{reporting_year})")
            
            pdf_reports.append({
                'year': reporting_year,
                'reporting_period_year': reporting_year,
                'search_year': year,
                'type': report_type,
                'title': original_title,
                'url': link,
                'source': 'serper',
                'source_page': source_page,
                'quarter': doc_quarter,  # Q1, Q2, Q3, Q4, or None for annual
                'period': period  # "Q4 2023" or "FY2023"
            })
        
        return pdf_reports
    
    def _get_significant_words(self, company: str) -> List[str]:
        """
        Extract significant identity words from company name.
        Excludes common suffixes like Ltd, Limited, Corporation, etc.
        """
        company_lower = company.lower()
        # Remove parenthetical content
        company_main = re.sub(r'\s*\([^)]*\)', '', company_lower).strip()
        company_words = company_main.split()
        
        common_words = [
            'inc', 'corp', 'corporation', 'ltd', 'limited', 'co', 'company',
            'the', 'and', 'of', 'group', 'holdings', 'international', 'pjsc',
            'oao', 'pao', 'jsc', 'plc', 'sa', 'ag', 'gmbh', 'llc', 'russian',
            'se', 'nv', 'bv', 'kk', 'ab', 'asa'
        ]
        
        # FIX: Allow 2-letter words for short company names (e.g. "OQ", "GE", "BP")
        return [word for word in company_words if len(word) >= 2 and word not in common_words]
    
    def _validate_company_domain(self, url: str, company: str) -> bool:
        """
        Validate that a URL domain matches the requested company.
        
        Returns True if:
        1. Domain contains company name word, OR
        2. Domain is a trusted regulator/exchange (BUT company name still checked later), OR
        3. Domain is a common CDN/cloud provider (BUT company name still checked later)
        4. Domain contains company abbreviation (e.g., KMG for KazMunayGas)
        
        CRITICAL: This function only does domain-level checks.
        Company name matching is done separately in _extract_pdf_urls STEP 4.
        """
        try:
            domain = urlparse(url).netloc.lower()
            # Remove common prefixes
            domain_clean = domain.replace('www.', '').replace('ir.', '')
            
            # TRUSTED DOMAINS: Allow these but company name is STILL verified in STEP 4
            # DO NOT return True here - just don't reject based on domain
            trusted_domains = [
                'sec.gov', 'sec.report', 'edgar',  # US SEC
                'jse.co.za',  # South Africa JSE
                'lse.co.uk', 'londonstockexchange',  # London
                'bse', 'nse',  # India
                'hkex',  # Hong Kong
                'kase.kz',  # Kazakhstan Stock Exchange
                'moex.com', 'moex.ru',  # Moscow Exchange
                'annualreports.com',  # Report aggregator
                'annualreport',
                'cloudfront.net', 'amazonaws.com',  # AWS CDN
                'akamai', 'fastly', 'cdn',  # CDNs
                'blob.core.windows.net',  # Azure
                'disclosure',  # Disclosure services
            ]
            
            # For trusted domains, we allow them but company name is verified in STEP 4
            if any(td in domain for td in trusted_domains):
                # IMPORTANT: Return True to pass domain check, but STEP 4 will verify company name
                return True
            
            significant_words = self._get_significant_words(company)
            
            # Check if domain contains any significant company word
            for word in significant_words:
                if word in domain_clean:
                    return True
            
            # Check abbreviation (e.g., "Dubai Mercantile Exchange" -> "dme")
            if len(significant_words) >= 2:
                abbreviation = ''.join(w[0] for w in significant_words)
                if len(abbreviation) >= 2 and abbreviation in domain_clean:
                    return True
            
            # Handle compound names like "KazMunayGas" -> extract abbreviation from CamelCase
            # Also handles single-word compound names
            company_clean = company.lower().strip()
            for word in company_clean.split():
                # Check if the word itself (without suffixes) is in domain
                if len(word) >= 3 and word in domain_clean:
                    return True
                # Extract CamelCase abbreviation (e.g., KazMunayGas -> kmg)
                caps = re.findall(r'[A-Z]', company)  # Find capital letters in original
                if len(caps) >= 2:
                    camel_abbrev = ''.join(caps).lower()
                    if camel_abbrev in domain_clean:
                        print(f"  [DEBUG] Domain match via CamelCase abbrev: '{camel_abbrev}' in '{domain_clean}'")
                        return True
            
            return False
        except Exception:
            return False
    
    def _find_investor_relations_page(self, company: str) -> Optional[str]:
        """
        Find the company's investor relations page URL.
        
        CRITICAL: Must find the COMPANY'S OWN website, NOT SEC/regulators.
        Prefers reports listing pages over generic IR homepage.
        """
        try:
            # Try multiple search strategies for different languages
            queries = [
                f'"{company}" "investor relations" "annual reports" site',
                f'"{company}" relaciones inversionistas informes anuales',  # Spanish
                f'"{company}" relations investisseurs rapports annuels',  # French
                f'"{company}" Investor Relations Geschäftsbericht',  # German
                f'"{company}" yatırımcı ilişkileri faaliyet raporu',  # Turkish
                f'"{company}" relações investidores relatório anual',  # Portuguese
                f'{company} investor relations reports',
            ]
            
            all_candidates = []
            
            for query in queries:
                print(f"\n[SEARCH] Searching for IR page: {query}")
                
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers={
                        'X-API-KEY': self.serper_key,
                        'Content-Type': 'application/json'
                    },
                    json={
                        'q': query,
                        'num': 10
                    },
                    timeout=5
                )
                
                if response.status_code != 200:
                    continue
                
                results = response.json()
                
                for result in results.get('organic', []):
                    link = result.get('link', '')
                    title = result.get('title', '').lower()
                    domain = urlparse(link).netloc.lower()
                    
                    # Skip PDF files
                    if link.endswith('.pdf'):
                        continue
                    
                    # EXCLUDE regulators/exchanges - we want company's OWN site
                    regulator_domains = ['sec.gov', 'edgar', 'hkex', 'jse.co.za', 'lse.co.uk', 'bse', 'nse']
                    if any(rd in domain for rd in regulator_domains):
                        print(f"  [X] Skipping regulator: {link[:50]}")
                        continue
                    
                    # Check domain contains company name word
                    significant_words = self._get_significant_words(company)
                    domain_clean = domain.replace('www.', '').replace('ir.', '')
                    
                    has_company_word = any(word in domain_clean for word in significant_words)
                    if not has_company_word:
                        print(f"  [X] Domain mismatch for '{company}': {domain}")
                        continue
                    
                    # Score the candidate
                    score = 0
                    link_lower = link.lower()
                    
                    # Prefer deeper reports pages (Spanish + English)
                    if '/financial' in link_lower or '/reports' in link_lower or '/informes' in link_lower:
                        score += 50
                    if '/annual' in link_lower or '/anuales' in link_lower or '/annuel' in link_lower:
                        score += 30
                    if 'investor' in link_lower or '/ir/' in link_lower or 'inversionista' in link_lower or 'investisseur' in link_lower or 'yatirimci' in link_lower:
                        score += 20
                    
                    # Prefer pages with reports in title (multilingual)
                    reports_keywords = ['financial', 'reports', 'informes', 'rapports', 'berichte', 'raporlar', 'relatorios']
                    if any(kw in title for kw in reports_keywords):
                        score += 20
                    annual_title_keywords = ['annual', 'anual', 'annuel', 'jahres', 'yıllık']
                    if any(kw in title for kw in annual_title_keywords):
                        score += 10
                        
                    all_candidates.append((score, link))
                    print(f"  [OK] Valid company domain (score {score}): {link[:60]}")
                
                # If we found good candidates, break early
                if len(all_candidates) >= 3:
                    break
            
            # Return highest-scored candidate
            if all_candidates:
                all_candidates.sort(reverse=True, key=lambda x: x[0])
                best_url = all_candidates[0][1]
                print(f"  [BEST] Selected: {best_url}")
                return best_url
            
            return None
            
        except Exception as e:
            print(f"Error finding IR page: {e}")
            return None
    
    def _validate_pdf_url(self, url: str) -> bool:
        """Validate that a URL is a valid PDF link."""
        if not url:
            return False
        
        if not url.startswith('http'):
            return False
        
        # Must contain .pdf
        if '.pdf' not in url.lower():
            return False
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))


def main():
    """Test the hybrid report finder."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python openai_report_finder.py 'query'")
        print("Example: python openai_report_finder.py 'Financial statements of Turkcell TCELL'")
        sys.exit(1)
    
    query = sys.argv[1]
    
    finder = OpenAISerperReportFinder()
    reports = finder.find_reports(query)
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    if not reports:
        print("No reports found")
    else:
        for report in reports:
            print(f"\n{report['year']}: {report['title']}")
            print(f"   URL: {report['url']}")


if __name__ == "__main__":
    main()
