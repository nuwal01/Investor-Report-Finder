"""
Financial Document Discovery Agent

Enhanced orchestrator for finding actual PDF documents (not just IR homepages).
Implements deep crawling of IR sites, subpage navigation, and fallback strategies.

HARD REQUIREMENTS:
- Do NOT stop at IR homepage - navigate deeper to find actual PDFs
- Only return direct PDF links
- Support multiple document types and year ranges
- Use fallback strategies for missing documents
"""

import os
import re
import logging
import time
import concurrent.futures
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from urllib.parse import urlparse, urljoin, parse_qs

import requests
from bs4 import BeautifulSoup

# Local imports
from .financial_keywords import (
    TIER_KEYWORDS,
    TIER_1_UNIVERSAL,
    TIER_2_PERIODIC,
    TIER_3_REGULATORY,
    TIER_4_INVESTOR_RELATIONS,
    TIER_7_URL_PATHS,
    TIER_8_MULTILINGUAL,
    get_all_keywords,
    get_url_path_patterns,
    detect_document_type,
    detect_language,
    is_english_version,
    get_language_preference_note,
    calculate_confidence_score,
    extract_year_from_text,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# NAVIGATION KEYWORDS FOR DEEP CRAWLING
# ============================================

# Pages that likely contain document links
IR_SUBPAGE_KEYWORDS = [
    "annual report", "annual reports",
    "reports", "report",
    "financial results", "results",
    "financial statements", "statements",
    "investor presentation", "presentations",
    "earnings", "earnings release",
    "quarterly", "quarterly report",
    "publications", "documents",
    "filings", "sec filings", "regulatory filings",
    "downloads", "pdf", "archive",
    "annual", "interim", "half-year",
    # Multilingual
    "jahresbericht", "geschäftsbericht",  # German
    "rapport annuel",  # French
    "informe anual",  # Spanish
]

# URL patterns indicating DEEP report listing pages (STRONG POSITIVES)
# These are pages that contain actual document links, not landing pages
REPORT_LISTING_PATTERNS = [
    # Report listing pages
    r'/reports',
    r'/report[s]?[-_]?and[-_]?presentations',
    r'/annual[-_]?report[s]?',
    r'/quarterly[-_]?report[s]?',
    r'/quarterly[-_]?results',
    r'/financial[-_]?results',
    r'/financial[-_]?statements',
    r'/financial[-_]?reports',
    r'/earnings[-_]?release[s]?',
    r'/earnings[-_]?report[s]?',
    r'/results[-_]?and[-_]?reports',
    # Publication/download pages
    r'/publications',
    r'/documents',
    r'/document[-_]?library',
    r'/downloads',
    r'/download[-_]?center',
    r'/filings',
    r'/sec[-_]?filings',
    r'/regulatory[-_]?filings',
    # Archive pages
    r'/archive[s]?',
    r'/news[-_]?and[-_]?reports',
    r'/presentations',
    r'/investor[-_]?presentations',
    # Nested paths
    r'/investors/reports',
    r'/investors/financial',
    r'/investor[-_]?relations/reports',
    r'/ir/reports',
    r'/ir/financial',
]

# URL patterns for IR LANDING PAGES (HARD NEGATIVES - reject as source_page)
# These are too shallow - we need to go deeper to find actual docs
IR_LANDING_PATTERNS = [
    r'^/investors?/?$',
    r'^/investor[-_]?relations?/?$',
    r'^/ir/?$',
    r'/investors?/overview',
    r'/investors?/home',
    r'/ir/overview',
    r'/corporate[-_]?governance/?$',
    r'/about[-_]?us/?$',
]

# ==========================================================================
# THIRD-PARTY RESEARCH BLOCKLIST (HARD REJECT)
# ==========================================================================

# Domains that publish third-party research/ratings (NOT company documents)
THIRD_PARTY_DOMAIN_BLOCKLIST = [
    # S&P / Standard & Poor's
    'spglobal.com', 'standardandpoors.com', 'ratingsdirect.com',
    'capitaliq.com', 'snl.com',
    # Moody's
    'moodys.com', 'moodysanalytics.com',
    # Fitch
    'fitchratings.com', 'fitchsolutions.com',
    # Other ratings/research
    'morningstar.com', 'refinitiv.com', 'bloomberg.com',
    'seekingalpha.com', 'tipranks.com', 'zacks.com',
    'thefly.com', 'benzinga.com', 'marketbeat.com',
    # News/aggregators
    'yahoo.com', 'google.com', 'reuters.com',
    'ft.com', 'wsj.com', 'cnbc.com',
    # Research portals
    'researchgate.net', 'ssrn.com', 'academia.edu',
]

# Title/content patterns that indicate third-party research (REJECT)
THIRD_PARTY_CONTENT_BLOCKLIST = [
    # S&P specific
    's&p', "standard & poor's", 'standard and poors',
    'ratingsdirect', 'ratings direct',
    # Credit ratings
    'credit rating', 'issuer credit', 'credit opinion',
    'rating action', 'outlook revised', 'rating affirmed',
    'ratings overview', 'creditwatch',
    # Research reports
    'research update', 'equity research', 'industry report',
    'analyst report', 'initiation of coverage', 'coverage update',
    'target price', 'price target', 'buy rating', 'sell rating',
    'hold rating', 'outperform', 'underperform',
    # Other third-party indicators
    "moody's", 'fitch ratings', 'morningstar report',
    'refinitiv', 'bloomberg intelligence',
]

# ==========================================================================
# OFFICIAL DOCUMENT IDENTIFIERS (POSITIVE SIGNALS - MUST MATCH 1+)
# ==========================================================================

# At least ONE of these must appear for a PDF to be accepted
OFFICIAL_DOCUMENT_SIGNALS = [
    # Annual reports
    'annual report', 'form 20-f', '20-f', 'form 10-k', '10-k',
    'geschäftsbericht', 'rapport annuel', 'informe anual',
    # Financial statements
    'financial statements', 'ifrs financial', 'consolidated financial',
    'audited financial', 'statutory accounts',
    'balance sheet', 'income statement', 'cash flow statement',
    # Quarterly/interim  
    'quarterly report', 'quarterly results', 'interim report',
    'form 10-q', '10-q', 'half-year', 'half year',
    # Earnings
    'earnings release', 'earnings report', 'results release',
    'financial results', 'results presentation',
    # Other official docs
    'management discussion', 'md&a', "management's discussion",
    'investor presentation', 'shareholder letter',
    'proxy statement', 'annual meeting',
]

# Official regulator/exchange domains (trusted sources)
OFFICIAL_REGULATOR_DOMAINS = [
    'sec.gov', 'sec.report',
    'londonstockexchange.com', 'lse.co.uk',
    'borsaistanbul.com', 'kap.org.tr',
    'hkex.com.hk', 'hkexnews.hk',
    'jpx.co.jp', 'tdnet.co.jp',
    'nyse.com', 'nasdaq.com',
    'euronext.com', 'deutsche-boerse.com',
    'moex.com', 'disclosure.ru',
    'asx.com.au', 'sgx.com',
]

# Legacy alias for compatibility
DOCUMENT_PAGE_URL_PATTERNS = REPORT_LISTING_PATTERNS


def is_third_party_source(url: str, text: str = "") -> bool:
    """
    Check if a URL or text indicates third-party research.
    Returns True if this is S&P, Moody's, or similar (should be REJECTED).
    """
    url_lower = url.lower()
    text_lower = text.lower() if text else ""
    
    # Check domain blocklist
    for blocked_domain in THIRD_PARTY_DOMAIN_BLOCKLIST:
        if blocked_domain in url_lower:
            return True
    
    # Check content blocklist
    combined = f"{url_lower} {text_lower}"
    for blocked_term in THIRD_PARTY_CONTENT_BLOCKLIST:
        if blocked_term in combined:
            return True
    
    return False


def has_official_document_signal(text: str, url: str = "") -> bool:
    """
    Check if text/URL contains signals of an official company document.
    At least ONE signal must be present for acceptance.
    """
    combined = f"{text.lower()} {url.lower()}"
    
    for signal in OFFICIAL_DOCUMENT_SIGNALS:
        if signal in combined:
            return True
    
    return False


def is_official_regulator_domain(url: str) -> bool:
    """Check if URL is from an official regulator/exchange."""
    url_lower = url.lower()
    for domain in OFFICIAL_REGULATOR_DOMAINS:
        if domain in url_lower:
            return True
    return False


def calculate_source_score(
    url: str,
    pdf_count: int,
    verified_domain: str = "",
    text: str = "",
) -> int:
    """
    Calculate source page score to choose the best source.
    
    Scoring:
    + 10 * pdf_count (matching PDFs on page)
    + 2 * path_depth (deeper = more specific)
    + 50 if official company/regulator domain
    - 1000 if third-party blocklist triggered
    - 50 if generic IR landing page
    """
    score = 0
    parsed = urlparse(url)
    path = parsed.path.lower()
    domain = parsed.netloc.lower()
    
    # PDF count bonus
    score += 10 * pdf_count
    
    # Path depth bonus
    path_depth = len([s for s in path.split('/') if s])
    score += 2 * path_depth
    
    # Official domain bonus
    if verified_domain and verified_domain.lower() in domain:
        score += 50
    if is_official_regulator_domain(url):
        score += 50
    
    # Third-party penalty (hard block)
    if is_third_party_source(url, text):
        score -= 1000
    
    # Landing page penalty
    for pattern in IR_LANDING_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            score -= 50
            break
    
    # Report listing bonus
    for pattern in REPORT_LISTING_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            score += 30
            break
    
    return score


def is_valid_source_page(url: str, has_pdfs: bool = False) -> bool:
    """
    Validate if a URL is a valid source_page for documents.
    
    A page is VALID if:
    - It matches REPORT_LISTING_PATTERNS (deep page), OR
    - It has PDFs and doesn't match IR_LANDING_PATTERNS
    
    A page is INVALID if:
    - It matches IR_LANDING_PATTERNS (shallow landing page)
    - AND does not have any PDFs
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Check for strong positive patterns (deep listing pages)
    for pattern in REPORT_LISTING_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return True
    
    # Check for hard negative patterns (landing pages)
    for pattern in IR_LANDING_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            # Landing page - only valid if it directly contains PDFs
            return has_pdfs
    
    # Neutral - accept if has PDFs
    return has_pdfs


def get_source_page_depth_score(url: str) -> int:
    """
    Score a URL by how deep/specific it is for report listing.
    Higher score = more specific/deeper page.
    
    Used to prefer deeper pages when multiple valid pages exist.
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    score = 0
    
    # More path segments = deeper
    score += len([s for s in path.split('/') if s]) * 10
    
    # Strong positive patterns increase score
    for pattern in REPORT_LISTING_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            score += 50
    
    # Landing page patterns decrease score
    for pattern in IR_LANDING_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            score -= 100
    
    return score


@dataclass
class DiscoveredDocument:
    """Represents a discovered financial document with all metadata."""
    company_name: str
    document_title: str
    reporting_period: str  # e.g., "2024", "Q3 2024", "H1 2024"
    document_type: str     # e.g., "annual_report", "10k", "quarterly_report"
    pdf_url: str           # Direct PDF URL
    source_page_url: str   # Page where document was found
    language: str          # Detected language
    confidence_score: float  # 0.0 to 1.0
    year: Optional[int] = None
    quarter: Optional[str] = None
    language_notes: Optional[str] = None  # Notes about language preference
    additional_metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_output_format(self) -> Dict:
        """Convert to the required output JSON schema with language info."""
        result = {
            "title": self.document_title,
            "doc_type": self.document_type,
            "period": self.reporting_period,
            "pdf_url": self.pdf_url,
            "source_page": self.source_page_url,
            "language": self.language,
        }
        if self.language_notes:
            result["notes"] = self.language_notes
        return result


@dataclass
class DiscoveryResult:
    """Complete discovery result in the required JSON schema."""
    company: str
    request: Dict
    documents: List[Dict]
    notes: str
    pages_checked: List[str] = field(default_factory=list)
    disambiguation_required: bool = False
    candidates: List[Dict] = field(default_factory=list)
    verified_company: Optional[str] = None
    
    def to_dict(self) -> Dict:
        result = {
            "company": self.company,
            "request": self.request,
            "documents": self.documents,
            "notes": self.notes,
        }
        if self.disambiguation_required:
            result["disambiguation_required"] = True
            result["candidates"] = self.candidates
            result["clarification_options"] = [
                "ticker symbol", "HQ country", "official website", "parent company"
            ]
        if self.verified_company:
            result["verified_company"] = self.verified_company
        return result


class FinancialDocumentDiscoveryAgent:
    """
    Enhanced agent for discovering financial documents with DEEP CRAWLING.
    
    Key Features:
    - Navigates beyond IR homepage to find actual PDFs
    - Crawls subpages (Reports, Publications, Filings, etc.)
    - Extracts PDFs from HTML viewer pages
    - Implements fallback search strategies
    - Returns structured JSON output
    """
    
    def __init__(
        self,
        serper_api_key: Optional[str] = None,
        tavily_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        max_crawl_depth: int = 3,
        request_delay: float = 1.0,
    ):
        """
        Initialize the discovery agent.
        
        Args:
            serper_api_key: Serper API key for Google search
            tavily_api_key: Tavily API key for web search
            openai_api_key: OpenAI API key for intelligent parsing
            max_crawl_depth: Maximum depth for crawling IR pages
            request_delay: Delay between requests (rate limiting)
        """
        self.serper_key = serper_api_key or os.getenv("SERPER_API_KEY")
        self.tavily_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.max_crawl_depth = max_crawl_depth
        self.request_delay = request_delay
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        # Track visited URLs to avoid loops
        self._visited_urls: Set[str] = set()
        self._pages_checked: List[str] = []
        
    def discover_documents(
        self,
        company: str,
        doc_types: Optional[List[str]] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        max_results: int = 50,
    ) -> DiscoveryResult:
        """
        Discover financial documents for a company.
        
        RETRIEVAL STRATEGY:
        1. Parse the user query
        2. Find the company's official IR domain
        3. Crawl/search within that domain for document pages
        4. Extract all PDF links matching criteria
        5. Apply fallback strategies if needed
        
        Args:
            company: Company name or ticker symbol
            doc_types: Document types requested (annual, quarterly, 10-k, etc.)
            start_year: Start year for search
            end_year: End year for search
            max_results: Maximum number of results
            
        Returns:
            DiscoveryResult with structured JSON output
        """
        logger.info(f"Starting deep document discovery for: {company}")
        
        # Reset state
        self._visited_urls = set()
        self._pages_checked = []
        
        # Set defaults
        current_year = datetime.now().year
        if not end_year:
            end_year = current_year
        if not start_year:
            start_year = end_year - 5
        if not doc_types:
            doc_types = ["annual report", "quarterly report", "financial statements", 
                        "earnings", "10-K", "10-Q", "20-F"]
        
        all_documents: List[DiscoveredDocument] = []
        
        # ========================================
        # Phase 0: Company Disambiguation
        # ========================================
        # Never trust first search result - verify company identity
        logger.info("Phase 0: Company disambiguation")
        verified_identity = None
        
        try:
            from .company_disambiguator import (
                CompanyDisambiguator, 
                CompanyIdentityCard, 
                AmbiguityError,
                extract_disambiguators_from_query,
            )
            
            disambiguator = CompanyDisambiguator(serper_api_key=self.serper_key)
            
            # Extract hints from company name
            hints = extract_disambiguators_from_query(company)
            
            disambiguation_result = disambiguator.disambiguate(
                company_name=company,
                hint_country=hints.get('hint_country'),
                hint_ticker=hints.get('hint_ticker'),
                hint_domain=hints.get('hint_domain'),
            )
            
            if isinstance(disambiguation_result, AmbiguityError):
                # Cannot verify company - return disambiguation request
                logger.warning(f"Company disambiguation failed: {disambiguation_result.message}")
                return DiscoveryResult(
                    company=company,
                    request={
                        "doc_types": doc_types,
                        "date_range": f"{start_year}-{end_year}"
                    },
                    documents=[],
                    notes=disambiguation_result.message,
                    disambiguation_required=True,
                    candidates=[
                        {
                            "name": c.canonical_name,
                            "domain": c.official_domain,
                            "country": c.hq_country,
                            "ticker": c.ticker,
                        }
                        for c in disambiguation_result.candidates
                    ],
                )
            
            verified_identity = disambiguation_result
            logger.info(f"Verified company: {verified_identity.canonical_name} (score: {verified_identity.confidence_score:.2f})")
            self._verified_identity = verified_identity
            
        except ImportError:
            logger.warning("Disambiguation module not available - proceeding without verification")
        except Exception as e:
            logger.warning(f"Disambiguation failed: {e} - proceeding without verification")
        
        # ========================================
        # Phase 1: Direct PDF Search via Google
        # ========================================
        logger.info("Phase 1: Direct PDF search")
        # Use verified company name if available
        search_company = verified_identity.canonical_name if verified_identity else company
        
        if self.serper_key:
            pdf_docs = self._search_direct_pdfs(search_company, doc_types, start_year, end_year)
            all_documents.extend(pdf_docs)
            logger.info(f"Direct PDF search found {len(pdf_docs)} documents")
        
        # ========================================
        # Phase 2: Find and Deep Crawl IR Site
        # ========================================
        logger.info("Phase 2: Deep IR site crawl")
        # Use verified IR URL if available, otherwise find it
        ir_page = verified_identity.ir_url if verified_identity and verified_identity.ir_url else None
        if not ir_page:
            ir_page = self._find_investor_relations_page(search_company)
        
        if ir_page:
            ir_docs = self._deep_crawl_ir_site(
                search_company, ir_page, doc_types, start_year, end_year
            )
            all_documents.extend(ir_docs)
            logger.info(f"IR crawl found {len(ir_docs)} documents")
        
        # ========================================
        # Phase 3: Fallback - SEC/Regulator Search
        # ========================================
        if len(all_documents) < 3:
            logger.info("Phase 3: Fallback regulator search")
            fallback_docs = self._search_regulatory_sources(
                company, doc_types, start_year, end_year
            )
            all_documents.extend(fallback_docs)
            logger.info(f"Fallback search found {len(fallback_docs)} documents")
        
        # ========================================
        # Phase 4: OpenRouter ChatGPT Fallback
        # ========================================
        # Triggered when all other methods fail to find documents
        if len(all_documents) == 0:
            logger.info("Phase 4: OpenRouter ChatGPT fallback (no documents found)")
            openrouter_docs = self._openrouter_fallback(
                company, doc_types, start_year, end_year
            )
            all_documents.extend(openrouter_docs)
            logger.info(f"OpenRouter fallback found {len(openrouter_docs)} documents")
        
        # ========================================
        # Phase 5: Deduplicate and Filter
        # ========================================
        unique_documents = self._deduplicate_documents(all_documents)
        
        # Filter to requested year range
        filtered_docs = [
            doc for doc in unique_documents
            if doc.year is None or (start_year <= doc.year <= end_year)
        ]
        
        # ========================================
        # Phase 6: Apply English-First Preference
        # ========================================
        filtered_docs = self._apply_english_preference(filtered_docs)
        
        # Sort by year descending, then by confidence
        filtered_docs.sort(key=lambda d: (d.year or 0, d.confidence_score), reverse=True)
        
        # Limit results
        final_documents = filtered_docs[:max_results]
        
        # Build notes
        if final_documents:
            notes = f"Found {len(final_documents)} document(s) matching criteria."
        else:
            notes = f"No PDF documents found for {company} in the requested range. " \
                   f"Pages checked: {len(self._pages_checked)}. " \
                   f"Try checking the company's official IR site directly."
        
        # Build result in required schema
        result = DiscoveryResult(
            company=company,
            request={
                "doc_types": doc_types,
                "date_range": f"{start_year}-{end_year}"
            },
            documents=[doc.to_output_format() for doc in final_documents],
            notes=notes,
            pages_checked=self._pages_checked[:10],  # Limit for output
            verified_company=verified_identity.canonical_name if verified_identity else None,
        )
        
        logger.info(f"Total unique documents found: {len(final_documents)}")
        return result
    
    def _search_direct_pdfs(
        self,
        company: str,
        doc_types: List[str],
        start_year: int,
        end_year: int,
    ) -> List[DiscoveredDocument]:
        """Search for direct PDF links via Google/Serper."""
        documents = []
        
        if not self.serper_key:
            return documents
        
        # Build targeted queries for each year and doc type
        for year in range(end_year, start_year - 1, -1):
            for doc_type in doc_types[:3]:  # Limit doc types per year
                queries = [
                    f'"{company}" "{doc_type}" {year} filetype:pdf',
                    f'"{company}" {doc_type} {year} annual report pdf',
                    f'{company} investor relations {year} {doc_type} filetype:pdf',
                ]
                
                for query in queries[:2]:  # Limit queries
                    try:
                        results = self._execute_serper_search(query)
                        docs = self._extract_pdfs_from_search(
                            company, results, year, doc_type
                        )
                        documents.extend(docs)
                        time.sleep(self.request_delay / 2)
                    except Exception as e:
                        logger.warning(f"Search failed: {e}")
        
        return documents
    
    def _execute_serper_search(self, query: str) -> Dict:
        """Execute a Serper API search."""
        response = self.session.post(
            'https://google.serper.dev/search',
            headers={
                'X-API-KEY': self.serper_key,
                'Content-Type': 'application/json'
            },
            json={
                'q': query,
                'num': 15
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Serper API error: {response.status_code}")
    
    def _extract_pdfs_from_search(
        self,
        company: str,
        results: Dict,
        year: int,
        doc_type: str,
    ) -> List[DiscoveredDocument]:
        """Extract PDF documents from search results."""
        documents = []
        
        for result in results.get('organic', []):
            url = result.get('link', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # Must be a PDF
            if '.pdf' not in url.lower():
                continue
            
            # Extract year from document
            detected_year = extract_year_from_text(f"{title} {url}")
            if not detected_year:
                detected_year = year
            
            # Detect document type
            doc_type_detected = detect_document_type(f"{title} {url}")
            
            # Calculate confidence
            tier_matches = self._count_tier_matches(f"{title} {snippet} {url}")
            confidence = calculate_confidence_score(
                has_pdf=True,
                has_year=detected_year is not None,
                tier_matches=tier_matches,
                has_url_path_match=True
            )
            
            # Build document
            document = DiscoveredDocument(
                company_name=company,
                document_title=title or f"{company} {doc_type} {year}",
                reporting_period=self._build_reporting_period(title, detected_year),
                document_type=doc_type_detected or doc_type,
                pdf_url=url,
                source_page_url=url,
                language=detect_language(title),
                confidence_score=confidence,
                year=detected_year,
                quarter=self._extract_quarter(title),
            )
            documents.append(document)
        
        return documents
    
    def _find_investor_relations_page(self, company: str) -> Optional[str]:
        """Find the company's investor relations page."""
        if not self.serper_key:
            return None
        
        try:
            # Try multiple search strategies
            queries = [
                f'"{company}" investor relations',
                f'{company} official investor relations annual reports',
                f'{company} IR financial reports',
            ]
            
            for query in queries:
                response = self.session.post(
                    'https://google.serper.dev/search',
                    headers={
                        'X-API-KEY': self.serper_key,
                        'Content-Type': 'application/json'
                    },
                    json={'q': query, 'num': 10},
                    timeout=10
                )
                
                if response.status_code != 200:
                    continue
                
                results = response.json()
                
                for result in results.get('organic', []):
                    url = result.get('link', '')
                    title = result.get('title', '').lower()
                    
                    # Skip PDFs - we want the page
                    if url.endswith('.pdf'):
                        continue
                    
                    # Look for IR page indicators
                    ir_indicators = [
                        'investor', 'ir.', '/ir/', '/ir-',
                        'shareholders', 'annual-report', 'financial'
                    ]
                    
                    if any(ind in url.lower() or ind in title for ind in ir_indicators):
                        logger.info(f"Found IR page: {url}")
                        self._pages_checked.append(url)
                        return url
                
                time.sleep(self.request_delay / 2)
        
        except Exception as e:
            logger.warning(f"Error finding IR page: {e}")
        
        return None
    
    def _deep_crawl_ir_site(
        self,
        company: str,
        ir_url: str,
        doc_types: List[str],
        start_year: int,
        end_year: int,
        depth: int = 0,
    ) -> List[DiscoveredDocument]:
        """
        Deep crawl the IR site to find actual PDF documents.
        
        This goes BEYOND the homepage - navigating to:
        - Reports & Presentations pages
        - Financial Results pages
        - Document archives
        - SEC Filings sections
        """
        documents = []
        
        if depth > self.max_crawl_depth:
            return documents
        
        # Normalize URL
        normalized_url = ir_url.rstrip('/').lower()
        if normalized_url in self._visited_urls:
            return documents
        
        self._visited_urls.add(normalized_url)
        self._pages_checked.append(ir_url)
        
        try:
            logger.info(f"Crawling (depth {depth}): {ir_url}")
            time.sleep(self.request_delay)
            
            response = self.session.get(ir_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # ========================================
            # Step 1: Extract PDFs from current page
            # ========================================
            pdf_docs = self._extract_pdfs_from_page(
                company, soup, ir_url, start_year, end_year
            )
            documents.extend(pdf_docs)
            logger.info(f"Found {len(pdf_docs)} PDFs on {ir_url}")
            
            # ========================================
            # Step 2: Find and crawl subpages
            # ========================================
            if depth < self.max_crawl_depth:
                subpage_urls = self._find_document_subpages(soup, ir_url)
                logger.info(f"Found {len(subpage_urls)} potential subpages to crawl")
                
                for subpage_url in subpage_urls[:5]:  # Limit subpages
                    sub_docs = self._deep_crawl_ir_site(
                        company, subpage_url, doc_types, 
                        start_year, end_year, depth + 1
                    )
                    documents.extend(sub_docs)
            
        except Exception as e:
            logger.warning(f"Error crawling {ir_url}: {e}")
        
        return documents
    
    def _extract_pdfs_from_page(
        self,
        company: str,
        soup: BeautifulSoup,
        page_url: str,
        start_year: int,
        end_year: int,
    ) -> List[DiscoveredDocument]:
        """Extract all PDF links from a page, filtering out third-party research."""
        documents = []
        rejected_third_party = 0
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Get the actual PDF URL
            pdf_url = self._resolve_pdf_url(href, page_url)
            if not pdf_url:
                continue
            
            # Skip duplicate URLs
            if pdf_url.lower() in self._visited_urls:
                continue
            self._visited_urls.add(pdf_url.lower())
            
            # Get link text and title
            link_text = link.get_text(strip=True) or ""
            title_attr = link.get('title', '')
            combined_text = f"{link_text} {title_attr} {pdf_url}"
            
            # ========================================
            # THIRD-PARTY FILTER (HARD REJECT)
            # ========================================
            if is_third_party_source(pdf_url, combined_text):
                logger.debug(f"Rejected third-party PDF: {pdf_url}")
                rejected_third_party += 1
                continue
            
            # ========================================
            # OFFICIAL DOCUMENT SIGNAL CHECK
            # ========================================
            # Must have at least one official signal unless from regulator
            if not is_official_regulator_domain(pdf_url):
                if not has_official_document_signal(combined_text, pdf_url):
                    logger.debug(f"Skipping PDF without official signal: {pdf_url}")
                    continue
            
            # Extract year
            detected_year = extract_year_from_text(combined_text)
            
            # Skip if outside year range (only if year is detected)
            if detected_year and not (start_year <= detected_year <= end_year):
                continue
            
            # Build document
            doc = self._create_document(
                company=company,
                title=link_text or title_attr or self._extract_filename(pdf_url),
                pdf_url=pdf_url,
                source_page=page_url,
                combined_text=combined_text,
                detected_year=detected_year,
            )
            documents.append(doc)
        
        if rejected_third_party > 0:
            logger.info(f"Rejected {rejected_third_party} third-party research PDFs on {page_url}")
        
        return documents
    
    def _resolve_pdf_url(self, href: str, base_url: str) -> Optional[str]:
        """
        Resolve a link to a direct PDF URL.
        
        Handles:
        - Direct .pdf links
        - Viewer URLs that contain PDF paths
        - Redirect URLs
        """
        # Clean the href
        href = href.strip()
        
        # Check if it's a direct PDF
        if '.pdf' in href.lower():
            return urljoin(base_url, href)
        
        # Check for PDF viewer URLs
        if 'viewer' in href.lower() or 'download' in href.lower():
            # Try to extract PDF URL from query params
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            
            for key in ['file', 'url', 'pdf', 'path', 'doc']:
                if key in params:
                    potential_pdf = params[key][0]
                    if '.pdf' in potential_pdf.lower():
                        return urljoin(base_url, potential_pdf)
        
        return None
    
    def _validate_pdf_url(self, url: str) -> bool:
        """
        Validate that a URL actually points to a PDF file.
        Uses HEAD request to check content type without downloading.
        """
        try:
            response = self.session.head(url, timeout=5, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Check if content type indicates PDF
            if 'application/pdf' in content_type:
                return True
            
            # Some servers don't set proper content type, check URL
            if response.status_code == 200 and '.pdf' in url.lower():
                return True
            
            return False
        except Exception:
            # If we can't validate, assume it's valid if URL looks like PDF
            return '.pdf' in url.lower()
    
    def _find_document_subpages(
        self,
        soup: BeautifulSoup,
        base_url: str,
    ) -> List[str]:
        """Find links to pages that likely contain documents."""
        subpages = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text(strip=True).lower()
            
            # Skip PDFs and external links
            if href.endswith('.pdf'):
                continue
            if href.startswith('mailto:') or href.startswith('javascript:'):
                continue
            
            # Build absolute URL
            abs_url = urljoin(base_url, href)
            
            # Check if link text suggests document page
            text_match = any(
                kw in link_text for kw in IR_SUBPAGE_KEYWORDS
            )
            
            # Check if URL pattern suggests document page
            url_match = any(
                re.search(pattern, abs_url.lower()) 
                for pattern in DOCUMENT_PAGE_URL_PATTERNS
            )
            
            if text_match or url_match:
                # Must be same domain
                if urlparse(abs_url).netloc == urlparse(base_url).netloc:
                    if abs_url not in self._visited_urls:
                        subpages.append(abs_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_subpages = []
        for url in subpages:
            normalized = url.rstrip('/').lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_subpages.append(url)
        
        return unique_subpages
    
    def _search_regulatory_sources(
        self,
        company: str,
        doc_types: List[str],
        start_year: int,
        end_year: int,
    ) -> List[DiscoveredDocument]:
        """Fallback: Search SEC and other regulatory sources."""
        documents = []
        
        if not self.serper_key:
            return documents
        
        # SEC EDGAR search
        queries = [
            f'site:sec.gov "{company}" 10-K filetype:pdf',
            f'site:sec.gov "{company}" 20-F annual report',
            f'"{company}" annual report {end_year} filetype:pdf official',
        ]
        
        for query in queries:
            try:
                results = self._execute_serper_search(query)
                for result in results.get('organic', []):
                    url = result.get('link', '')
                    title = result.get('title', '')
                    
                    if '.pdf' not in url.lower():
                        continue
                    
                    detected_year = extract_year_from_text(f"{title} {url}")
                    if detected_year and not (start_year <= detected_year <= end_year):
                        continue
                    
                    doc = self._create_document(
                        company=company,
                        title=title,
                        pdf_url=url,
                        source_page=url,
                        combined_text=f"{title} {url}",
                        detected_year=detected_year,
                    )
                    documents.append(doc)
                
                time.sleep(self.request_delay / 2)
            except Exception as e:
                logger.warning(f"Regulatory search failed: {e}")
        
        return documents
    
    def _openrouter_fallback(
        self,
        company: str,
        doc_types: List[str],
        start_year: int,
        end_year: int,
    ) -> List[DiscoveredDocument]:
        """
        OpenRouter ChatGPT fallback when all other methods fail.
        
        Uses LLM's knowledge to find investor documents.
        """
        documents = []
        
        try:
            from .openrouter_fallback import OpenRouterFallbackRetriever
            
            # Check if OpenRouter is configured
            openrouter_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not openrouter_key:
                logger.warning("OpenRouter fallback skipped: No API key configured")
                return documents
            
            retriever = OpenRouterFallbackRetriever(api_key=openrouter_key)
            result = retriever.retrieve_documents(
                company=company,
                doc_types=doc_types,
                start_year=start_year,
                end_year=end_year,
            )
            
            # Convert results to DiscoveredDocument objects
            for doc_dict in result.get('documents', []):
                detected_year = None
                period = doc_dict.get('period', '')
                year_match = re.search(r'(20\d{2})', period)
                if year_match:
                    detected_year = int(year_match.group(1))
                
                doc = DiscoveredDocument(
                    company_name=company,
                    document_title=doc_dict.get('title', 'Financial Document'),
                    reporting_period=period,
                    document_type=doc_dict.get('doc_type', 'annual_report'),
                    pdf_url=doc_dict.get('pdf_url', ''),
                    source_page_url=doc_dict.get('source_page', ''),
                    language='english',
                    confidence_score=0.7,  # Lower confidence for LLM-sourced results
                    year=detected_year,
                    additional_metadata={'source': 'openrouter_fallback'}
                )
                documents.append(doc)
            
            # Store IR page if found
            ir_page = result.get('ir_reports_page')
            if ir_page:
                self._pages_checked.append(f"[OpenRouter Found] {ir_page}")
            
            logger.info(f"OpenRouter fallback retrieved {len(documents)} documents")
            
        except ImportError:
            logger.warning("OpenRouter fallback skipped: openrouter_fallback module not available")
        except Exception as e:
            logger.error(f"OpenRouter fallback failed: {e}")
        
        return documents
    
    def _create_document(
        self,
        company: str,
        title: str,
        pdf_url: str,
        source_page: str,
        combined_text: str,
        detected_year: Optional[int],
    ) -> DiscoveredDocument:
        """Create a DiscoveredDocument with all metadata."""
        tier_matches = self._count_tier_matches(combined_text)
        
        doc_type = detect_document_type(combined_text)
        language = detect_language(title)
        quarter = self._extract_quarter(title)
        
        confidence = calculate_confidence_score(
            has_pdf=True,
            has_year=detected_year is not None,
            tier_matches=tier_matches,
            has_url_path_match=any(p in pdf_url.lower() for p in TIER_7_URL_PATHS)
        )
        
        reporting_period = self._build_reporting_period(title, detected_year)
        
        return DiscoveredDocument(
            company_name=company,
            document_title=title or "Financial Document",
            reporting_period=reporting_period,
            document_type=doc_type or "financial_document",
            pdf_url=pdf_url,
            source_page_url=source_page,
            language=language,
            confidence_score=confidence,
            year=detected_year,
            quarter=quarter,
            additional_metadata={'tier_matches': tier_matches}
        )
    
    def _count_tier_matches(self, text: str) -> Dict[int, int]:
        """Count keyword matches per tier."""
        text_lower = text.lower()
        matches = {}
        
        for tier, keywords in TIER_KEYWORDS.items():
            count = 0
            if tier == 8:  # Multilingual tier is a dict
                for lang_keywords in keywords.values():
                    for kw in lang_keywords:
                        if kw.lower() in text_lower:
                            count += 1
            else:
                for kw in keywords:
                    if kw.lower() in text_lower:
                        count += 1
            matches[tier] = count
        
        return matches
    
    def _extract_quarter(self, text: str) -> Optional[str]:
        """Extract quarter from text."""
        text_lower = text.lower()
        if 'q1' in text_lower or 'first quarter' in text_lower:
            return 'Q1'
        elif 'q2' in text_lower or 'second quarter' in text_lower:
            return 'Q2'
        elif 'q3' in text_lower or 'third quarter' in text_lower:
            return 'Q3'
        elif 'q4' in text_lower or 'fourth quarter' in text_lower:
            return 'Q4'
        elif 'h1' in text_lower or 'half year' in text_lower or 'first half' in text_lower:
            return 'H1'
        elif 'h2' in text_lower or 'second half' in text_lower:
            return 'H2'
        return None
    
    def _build_reporting_period(self, text: str, year: Optional[int]) -> str:
        """Build reporting period string."""
        quarter = self._extract_quarter(text)
        if quarter and year:
            return f"{quarter} {year}"
        elif year:
            return str(year)
        else:
            return "Unknown"
    
    def _extract_filename(self, url: str) -> str:
        """Extract filename from URL."""
        parsed = urlparse(url)
        path = parsed.path
        filename = path.split('/')[-1]
        # Remove .pdf extension for cleaner title
        if filename.lower().endswith('.pdf'):
            filename = filename[:-4]
        # Replace underscores and dashes with spaces
        filename = filename.replace('_', ' ').replace('-', ' ')
        return filename
    
    def _apply_english_preference(
        self,
        documents: List[DiscoveredDocument],
    ) -> List[DiscoveredDocument]:
        """
        Apply English-first preference to documents.
        
        For each report (year/type combination):
        - If English PDF exists, prefer it
        - If no English PDF, return original with note
        - Never return duplicates (same year/type)
        """
        from collections import defaultdict
        
        # Group documents by year and type
        grouped: Dict[tuple, List[DiscoveredDocument]] = defaultdict(list)
        
        for doc in documents:
            key = (doc.year, doc.document_type)
            grouped[key].append(doc)
        
        result = []
        
        for key, docs in grouped.items():
            # Check if any English version exists for this year/type
            english_docs = [d for d in docs if is_english_version(d.pdf_url, d.document_title)]
            non_english_docs = [d for d in docs if not is_english_version(d.pdf_url, d.document_title)]
            
            if english_docs:
                # Prefer English version(s)
                for doc in english_docs:
                    doc.language_notes = "English version"
                    result.append(doc)
            elif non_english_docs:
                # No English available - return original with note
                best_doc = max(non_english_docs, key=lambda d: d.confidence_score)
                best_doc.language_notes = get_language_preference_note(
                    best_doc.language, english_available=False
                )
                result.append(best_doc)
        
        logger.info(f"English preference: {len(documents)} -> {len(result)} documents after filtering")
        return result
    
    def _deduplicate_documents(
        self,
        documents: List[DiscoveredDocument],
    ) -> List[DiscoveredDocument]:
        """Remove duplicate documents by URL."""
        seen_urls = set()
        unique = []
        
        for doc in documents:
            normalized_url = doc.pdf_url.lower().rstrip('/')
            
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique.append(doc)
        
        return unique


def discover_investor_documents(
    query: str,
    serper_api_key: Optional[str] = None,
) -> Dict:
    """
    High-level function to discover documents from a natural language query.
    
    Example: "Annual reports for Global Ports Delo Group from 2020 to 2024"
    
    Returns the exact JSON schema required:
    {
        "company": "string",
        "request": {"doc_types": [...], "date_range": "string"},
        "documents": [...],
        "notes": "string"
    }
    """
    # Parse query
    company, doc_types, start_year, end_year = _parse_query(query)
    
    # Initialize agent
    agent = FinancialDocumentDiscoveryAgent(
        serper_api_key=serper_api_key or os.getenv("SERPER_API_KEY")
    )
    
    # Discover documents
    result = agent.discover_documents(
        company=company,
        doc_types=doc_types,
        start_year=start_year,
        end_year=end_year,
    )
    
    return result.to_dict()


def _parse_query(query: str) -> Tuple[str, List[str], int, int]:
    """Parse natural language query into components."""
    query_lower = query.lower()
    
    # Extract year range
    year_match = re.search(r'(\d{4})\s*(?:to|-)\s*(\d{4})', query)
    if year_match:
        start_year = int(year_match.group(1))
        end_year = int(year_match.group(2))
    else:
        # Try single year
        single_year = re.search(r'\b(20\d{2})\b', query)
        if single_year:
            end_year = int(single_year.group(1))
            start_year = end_year
        else:
            end_year = datetime.now().year
            start_year = end_year - 5
    
    # Extract document types
    doc_types = []
    type_patterns = [
        (r'annual\s*report', 'annual report'),
        (r'quarterly\s*report', 'quarterly report'),
        (r'quarterly\s*earnings', 'quarterly earnings'),
        (r'financial\s*statements?', 'financial statements'),
        (r'investor\s*presentation', 'investor presentation'),
        (r'earnings\s*release', 'earnings release'),
        (r'10-k', '10-K'),
        (r'10-q', '10-Q'),
        (r'20-f', '20-F'),
    ]
    
    for pattern, doc_type in type_patterns:
        if re.search(pattern, query_lower):
            doc_types.append(doc_type)
    
    if not doc_types:
        doc_types = ['annual report']  # Default
    
    # Extract company name
    # Remove common phrases to find company name
    company = query
    for phrase in ['annual reports for', 'annual report for', 'reports for', 
                   'from', 'to', 'between', str(start_year), str(end_year)]:
        company = re.sub(phrase, '', company, flags=re.IGNORECASE)
    
    # Also remove doc type phrases
    for _, doc_type in type_patterns:
        company = re.sub(doc_type, '', company, flags=re.IGNORECASE)
    
    company = ' '.join(company.split()).strip()
    
    return company, doc_types, start_year, end_year


def main():
    """Test the enhanced discovery agent."""
    print("=" * 70)
    print("Financial Document Discovery Agent - Deep Crawl Test")
    print("=" * 70)
    
    # Test query
    query = "Annual reports for Apple from 2022 to 2024"
    print(f"\nQuery: {query}\n")
    
    result = discover_investor_documents(query)
    
    import json
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
