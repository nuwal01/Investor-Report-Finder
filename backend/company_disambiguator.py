"""
Company Disambiguator Module

Implements strict company identity verification to prevent fetching
documents from the wrong company due to name collisions.

Key Features:
- Collects 3-8 candidates per query (never trust first result)
- Verifies identity using multiple signals
- Builds Company Identity Cards
- Handles ambiguity with user clarification
- Validates PDF domains
"""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, Tuple
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ==========================================================================
# CONSTANTS
# ==========================================================================

# Query patterns for candidate collection
DISAMBIGUATION_QUERIES = [
    '"{company}" official website',
    '"{company}" investor relations',
    '"{company}" annual report pdf',
    '"{company}" headquarters address',
    '"{company}" ticker exchange stock',
    '"{company}" wikipedia',
    '"{company}" SEC EDGAR filing',
    '"{company}" stock exchange listing',
]

# Official regulator domains (PDFs from these are trusted)
OFFICIAL_REGULATORS = [
    'sec.gov',
    'sec.report',
    'londonstockexchange.com',
    'borsaistanbul.com',
    'hkex.com.hk',
    'jpx.co.jp',
    'nyse.com',
    'nasdaq.com',
    'euronext.com',
    'deutsche-boerse.com',
    'moex.com',
]

# Industry keywords for mismatch detection
INDUSTRY_KEYWORDS = {
    'ports': ['port', 'terminal', 'container', 'shipping', 'maritime', 'cargo', 'logistics'],
    'cruise': ['cruise', 'passenger', 'tourism', 'travel', 'vacation'],
    'finance': ['bank', 'investment', 'asset', 'fund', 'capital', 'securities'],
    'tech': ['software', 'technology', 'digital', 'platform', 'saas', 'cloud'],
    'energy': ['oil', 'gas', 'energy', 'power', 'renewable', 'solar'],
    'retail': ['retail', 'store', 'shop', 'consumer', 'ecommerce'],
}

# Domains that are always blockers (aggregators, directories)
BLOCKER_DOMAINS = [
    'wikipedia.org',
    'bloomberg.com',
    'reuters.com',
    'yahoo.com',
    'marketwatch.com',
    'crunchbase.com',
    'linkedin.com',
    'facebook.com',
    'twitter.com',
    'glassdoor.com',
    'indeed.com',
]


# ==========================================================================
# DATA CLASSES
# ==========================================================================

@dataclass
class CandidateCompany:
    """A candidate company found during search."""
    name: str
    domain: str
    url: str
    source_query: str
    snippet: str = ""
    

@dataclass
class CompanyIdentityCard:
    """Verified company identity with all proof signals."""
    canonical_name: str
    known_aliases: List[str] = field(default_factory=list)
    hq_country: str = ""
    industry_keywords: List[str] = field(default_factory=list)
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    official_domain: str = ""
    ir_url: Optional[str] = None
    confidence_score: float = 0.0
    proof_links: List[str] = field(default_factory=list)
    signals: Dict[str, bool] = field(default_factory=dict)
    
    def meets_threshold(self) -> bool:
        """Check if identity meets acceptance threshold."""
        strong_signals = sum(1 for k, v in self.signals.items() 
                           if v and k.startswith('strong_'))
        return self.confidence_score >= 0.80 and strong_signals >= 2


@dataclass
class AmbiguityError:
    """Returned when company cannot be disambiguated."""
    message: str = "Multiple companies match this name. Please provide additional details."
    candidates: List[CompanyIdentityCard] = field(default_factory=list)
    clarification_options: List[str] = field(default_factory=lambda: [
        "ticker symbol (e.g., GPRT)",
        "HQ country (e.g., Turkey, Russia)",
        "official website domain",
        "parent company or group name",
    ])
    
    def to_dict(self) -> Dict:
        return {
            "disambiguation_required": True,
            "message": self.message,
            "candidates": [
                {
                    "name": c.canonical_name,
                    "domain": c.official_domain,
                    "country": c.hq_country,
                    "ticker": c.ticker,
                    "confidence": c.confidence_score,
                }
                for c in self.candidates
            ],
            "clarification_options": self.clarification_options,
        }


# ==========================================================================
# COMPANY DISAMBIGUATOR
# ==========================================================================

class CompanyDisambiguator:
    """
    Strict company disambiguation to prevent wrong company matches.
    
    Workflow:
    1. Collect 3-8 candidates using multiple search queries
    2. Verify each candidate with scoring signals
    3. Build identity cards for top candidates
    4. Resolve ambiguity or request clarification
    """
    
    def __init__(
        self,
        serper_api_key: Optional[str] = None,
        request_delay: float = 0.5,
    ):
        self.serper_key = serper_api_key or os.getenv("SERPER_API_KEY")
        self.request_delay = request_delay
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def disambiguate(
        self,
        company_name: str,
        hint_country: Optional[str] = None,
        hint_ticker: Optional[str] = None,
        hint_domain: Optional[str] = None,
    ) -> Union[CompanyIdentityCard, AmbiguityError]:
        """
        Disambiguate a company name to a verified identity.
        
        Args:
            company_name: User-provided company name
            hint_country: Optional country hint for disambiguation
            hint_ticker: Optional ticker hint
            hint_domain: Optional domain hint
            
        Returns:
            CompanyIdentityCard if verified, AmbiguityError if ambiguous
        """
        logger.info(f"Disambiguating company: {company_name}")
        
        # Step 1: Collect candidates
        candidates = self._collect_candidates(company_name)
        logger.info(f"Collected {len(candidates)} candidates")
        
        if not candidates:
            return AmbiguityError(
                message=f"Could not find any companies matching '{company_name}'",
                candidates=[],
            )
        
        # Step 2: Build identity cards with verification
        identity_cards = []
        for candidate in candidates[:8]:  # Limit to top 8
            card = self._build_identity_card(candidate, company_name)
            if card and not self._has_hard_blockers(card, company_name):
                identity_cards.append(card)
        
        logger.info(f"Built {len(identity_cards)} identity cards")
        
        if not identity_cards:
            return AmbiguityError(
                message=f"Could not verify any companies matching '{company_name}'",
                candidates=[],
            )
        
        # Step 3: Apply hints to filter candidates
        if hint_country or hint_ticker or hint_domain:
            identity_cards = self._apply_hints(
                identity_cards, hint_country, hint_ticker, hint_domain
            )
        
        # Step 4: Check for clear winner
        identity_cards.sort(key=lambda c: c.confidence_score, reverse=True)
        
        top_card = identity_cards[0]
        
        # Check if top card meets threshold
        if top_card.meets_threshold():
            # Check if there's a close second (ambiguity)
            if len(identity_cards) > 1:
                second_card = identity_cards[1]
                score_diff = top_card.confidence_score - second_card.confidence_score
                
                if score_diff < 0.15:  # Too close - ambiguous
                    logger.warning(f"Ambiguous: top scores {top_card.confidence_score:.2f} vs {second_card.confidence_score:.2f}")
                    return AmbiguityError(
                        message=f"Multiple companies match '{company_name}'. Please clarify.",
                        candidates=identity_cards[:3],
                    )
            
            logger.info(f"Verified company: {top_card.canonical_name} (score: {top_card.confidence_score:.2f})")
            return top_card
        
        # Top card doesn't meet threshold
        return AmbiguityError(
            message=f"Could not confidently verify '{company_name}'. Please provide more details.",
            candidates=identity_cards[:3],
        )
    
    def _collect_candidates(self, company_name: str) -> List[CandidateCompany]:
        """Collect 3-8 candidates using multiple search queries."""
        candidates = []
        seen_domains = set()
        
        if not self.serper_key:
            logger.warning("No Serper key - limited candidate collection")
            return candidates
        
        # Run multiple search queries
        for query_template in DISAMBIGUATION_QUERIES[:6]:
            query = query_template.format(company=company_name)
            
            try:
                results = self._serper_search(query)
                
                for result in results.get('organic', [])[:3]:
                    url = result.get('link', '')
                    domain = urlparse(url).netloc.lower()
                    
                    # Skip duplicates and blockers
                    if domain in seen_domains:
                        continue
                    if any(blocker in domain for blocker in BLOCKER_DOMAINS):
                        continue
                    
                    seen_domains.add(domain)
                    
                    candidate = CandidateCompany(
                        name=result.get('title', ''),
                        domain=domain,
                        url=url,
                        source_query=query,
                        snippet=result.get('snippet', ''),
                    )
                    candidates.append(candidate)
                    
                    if len(candidates) >= 8:
                        break
                        
            except Exception as e:
                logger.warning(f"Search failed: {e}")
            
            if len(candidates) >= 8:
                break
        
        return candidates
    
    def _build_identity_card(
        self,
        candidate: CandidateCompany,
        search_name: str,
    ) -> Optional[CompanyIdentityCard]:
        """Build and verify an identity card for a candidate."""
        try:
            # Fetch the candidate page
            response = self.session.get(candidate.url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            page_text = soup.get_text(separator=' ', strip=True).lower()
            
            # Initialize card
            card = CompanyIdentityCard(
                canonical_name=self._extract_legal_name(soup, search_name),
                official_domain=candidate.domain,
                proof_links=[candidate.url],
            )
            
            # Calculate signals
            signals = {}
            score = 0.0
            
            # Strong Signal 1: Legal name match (0.25)
            name_match = self._check_name_match(page_text, search_name)
            signals['strong_legal_name'] = name_match
            if name_match:
                score += 0.25
            
            # Strong Signal 2: IR path exists (0.25)
            ir_url = self._find_ir_page(soup, candidate.url)
            signals['strong_ir_path'] = ir_url is not None
            if ir_url:
                score += 0.25
                card.ir_url = ir_url
            
            # Strong Signal 3: Ticker/exchange match (0.25)
            ticker, exchange = self._extract_ticker(soup, page_text)
            signals['strong_ticker'] = ticker is not None
            if ticker:
                score += 0.25
                card.ticker = ticker
                card.exchange = exchange
            
            # Strong Signal 4: Contact/country match (0.25)
            country = self._extract_country(soup, page_text)
            signals['strong_contact'] = country is not None
            if country:
                score += 0.15  # Slightly lower weight
                card.hq_country = country
            
            # Medium Signal: Industry keywords (0.10)
            industry = self._detect_industry(page_text)
            signals['medium_industry'] = len(industry) > 0
            if industry:
                score += 0.10
                card.industry_keywords = industry
            
            card.signals = signals
            card.confidence_score = min(score, 1.0)
            
            return card
            
        except Exception as e:
            logger.warning(f"Failed to build identity card for {candidate.domain}: {e}")
            return None
    
    def _has_hard_blockers(self, card: CompanyIdentityCard, search_name: str) -> bool:
        """Check for hard blockers that should reject a candidate."""
        # Check for partial name mismatch
        search_words = set(search_name.lower().split())
        canonical_words = set(card.canonical_name.lower().split())
        
        # If canonical name has significantly different key words, block
        key_diffs = search_words.symmetric_difference(canonical_words)
        important_diffs = [w for w in key_diffs if len(w) > 3 and w not in ['plc', 'ltd', 'inc', 'corp', 'llc', 'group', 'holding', 'holdings']]
        
        if len(important_diffs) > 2:
            logger.debug(f"Blocker: name mismatch - {search_name} vs {card.canonical_name}")
            return True
        
        return False
    
    def _apply_hints(
        self,
        cards: List[CompanyIdentityCard],
        country: Optional[str],
        ticker: Optional[str],
        domain: Optional[str],
    ) -> List[CompanyIdentityCard]:
        """Apply user hints to filter/boost candidates."""
        if country:
            country_lower = country.lower()
            for card in cards:
                if card.hq_country and country_lower in card.hq_country.lower():
                    card.confidence_score += 0.20
        
        if ticker:
            ticker_upper = ticker.upper()
            for card in cards:
                if card.ticker and ticker_upper == card.ticker.upper():
                    card.confidence_score += 0.30
        
        if domain:
            domain_lower = domain.lower()
            for card in cards:
                if domain_lower in card.official_domain.lower():
                    card.confidence_score += 0.30
        
        return cards
    
    # ======================================================================
    # EXTRACTION HELPERS
    # ======================================================================
    
    def _extract_legal_name(self, soup: BeautifulSoup, fallback: str) -> str:
        """Extract legal company name from page."""
        # Try meta tags first
        for meta in soup.find_all('meta'):
            if meta.get('property') == 'og:site_name':
                return meta.get('content', fallback)
        
        # Try title
        if soup.title:
            title = soup.title.get_text(strip=True)
            # Clean up title
            for sep in [' | ', ' - ', ' :: ', ' — ']:
                if sep in title:
                    title = title.split(sep)[0]
            return title
        
        return fallback
    
    def _check_name_match(self, page_text: str, search_name: str) -> bool:
        """Check if the search name appears on the page."""
        search_lower = search_name.lower()
        
        # Exact match
        if search_lower in page_text:
            return True
        
        # Check for key words (excluding common suffixes)
        key_words = [w for w in search_lower.split() 
                    if len(w) > 3 and w not in ['plc', 'ltd', 'inc', 'corp', 'llc', 'group']]
        
        matches = sum(1 for w in key_words if w in page_text)
        return matches >= len(key_words) * 0.7
    
    def _find_ir_page(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Find investor relations page link."""
        ir_patterns = [
            'investor', 'investors', 'ir', 'investor-relations',
            'investor relations', 'financial', 'shareholders',
        ]
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            
            for pattern in ir_patterns:
                if pattern in href or pattern in text:
                    full_url = urljoin(base_url, link['href'])
                    return full_url
        
        return None
    
    def _extract_ticker(self, soup: BeautifulSoup, page_text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract ticker symbol and exchange."""
        # Common patterns
        patterns = [
            r'(?:ticker|symbol)[\s:]+([A-Z]{2,5})',
            r'(?:NYSE|NASDAQ|LSE|BIST)[\s:]+([A-Z]{2,5})',
            r'\(([A-Z]{2,5})\)',  # (GPRT)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                ticker = match.group(1).upper()
                
                # Try to find exchange
                exchange = None
                for ex in ['NYSE', 'NASDAQ', 'LSE', 'BIST', 'MOEX', 'HKEX']:
                    if ex.lower() in page_text:
                        exchange = ex
                        break
                
                return ticker, exchange
        
        return None, None
    
    def _extract_country(self, soup: BeautifulSoup, page_text: str) -> Optional[str]:
        """Extract headquarters country."""
        countries = [
            'turkey', 'russia', 'united states', 'usa', 'uk', 'united kingdom',
            'germany', 'france', 'china', 'japan', 'india', 'brazil',
            'netherlands', 'switzerland', 'singapore', 'hong kong',
        ]
        
        for country in countries:
            if country in page_text:
                return country.title()
        
        return None
    
    def _detect_industry(self, page_text: str) -> List[str]:
        """Detect industry keywords from page text."""
        detected = []
        
        for industry, keywords in INDUSTRY_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in page_text)
            if matches >= 2:
                detected.append(industry)
        
        return detected
    
    def _serper_search(self, query: str) -> Dict:
        """Execute Serper search."""
        response = requests.post(
            'https://google.serper.dev/search',
            headers={'X-API-KEY': self.serper_key, 'Content-Type': 'application/json'},
            json={'q': query, 'num': 5},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    
    # ======================================================================
    # PDF DOMAIN VALIDATION
    # ======================================================================
    
    def validate_pdf_domain(
        self,
        pdf_url: str,
        verified_identity: CompanyIdentityCard,
    ) -> bool:
        """
        Validate that a PDF is from a trusted source.
        
        Accepts if:
        - PDF is from the verified official domain
        - PDF is from an official regulator domain
        """
        pdf_domain = urlparse(pdf_url).netloc.lower()
        verified_domain = verified_identity.official_domain.lower()
        
        # Check official domain
        if verified_domain in pdf_domain or pdf_domain in verified_domain:
            return True
        
        # Check regulators
        for regulator in OFFICIAL_REGULATORS:
            if regulator in pdf_domain:
                return True
        
        logger.warning(f"PDF domain {pdf_domain} not verified for {verified_identity.canonical_name}")
        return False


# ==========================================================================
# UTILITY FUNCTIONS
# ==========================================================================

def extract_disambiguators_from_query(query: str) -> Dict[str, Optional[str]]:
    """
    Extract disambiguation hints from a natural language query.
    
    Examples:
    - "Global Ports Holding Turkey" -> hint_country: "Turkey"
    - "Apple (AAPL)" -> hint_ticker: "AAPL"
    """
    hints = {
        'hint_country': None,
        'hint_ticker': None,
        'hint_domain': None,
    }
    
    # Extract ticker from parentheses
    ticker_match = re.search(r'\(([A-Z]{2,5})\)', query)
    if ticker_match:
        hints['hint_ticker'] = ticker_match.group(1)
    
    # Extract country
    countries = ['turkey', 'russia', 'usa', 'uk', 'germany', 'china', 'japan', 'india']
    query_lower = query.lower()
    for country in countries:
        if country in query_lower:
            hints['hint_country'] = country.title()
            break
    
    # Extract domain hints
    domain_match = re.search(r'([a-z0-9-]+\.(com|co|net|org|io))', query.lower())
    if domain_match:
        hints['hint_domain'] = domain_match.group(0)
    
    return hints


if __name__ == "__main__":
    # Test the disambiguator
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    disambiguator = CompanyDisambiguator()
    
    test_company = sys.argv[1] if len(sys.argv) > 1 else "Global Ports Holding"
    print(f"\nDisambiguating: {test_company}")
    print("=" * 60)
    
    result = disambiguator.disambiguate(test_company)
    
    if isinstance(result, CompanyIdentityCard):
        print(f"\n✅ Verified Company:")
        print(f"   Name: {result.canonical_name}")
        print(f"   Domain: {result.official_domain}")
        print(f"   Country: {result.hq_country}")
        print(f"   Ticker: {result.ticker}")
        print(f"   IR URL: {result.ir_url}")
        print(f"   Confidence: {result.confidence_score:.2f}")
        print(f"   Signals: {result.signals}")
    else:
        print(f"\n⚠️ Disambiguation Required:")
        print(f"   Message: {result.message}")
        print(f"   Candidates: {len(result.candidates)}")
        for c in result.candidates:
            print(f"     - {c.canonical_name} ({c.official_domain}) score={c.confidence_score:.2f}")
