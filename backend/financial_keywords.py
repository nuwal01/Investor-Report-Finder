"""
Financial Document Discovery Keywords Module

Comprehensive keyword dictionary for maximum recall when discovering
financial documents, regulatory filings, and investor reports worldwide.

Contains 8 tiers of search terms organized by priority and specificity.
"""

from typing import Dict, List, Set
import re

# ==========================================================================
# TIER 1 — UNIVERSAL FINANCIAL REPORT TERMS (HIGHEST PRIORITY)
# ==========================================================================
TIER_1_UNIVERSAL = [
    "financial statements",
    "financial report",
    "annual report",
    "annual financial statements",
    "audited financial statements",
    "unaudited financial statements",
    "consolidated financial statements",
    "standalone financial statements",
    "statutory accounts",
    "statutory report",
    "financial disclosure",
    "financial information",
    "financial performance",
    "financial results",
]

# ==========================================================================
# TIER 2 — ANNUAL & PERIODIC REPORTING TERMS
# ==========================================================================
TIER_2_PERIODIC = [
    # Annual terms
    "annual filing",
    "yearly report",
    "year-end report",
    "annual accounts",
    "annual results",
    "full year results",
    "FY results",
    "FY report",
    "yearly financial report",
    "periodic report",
    
    # Quarterly terms
    "quarterly report",
    "quarterly results",
    "Q1 report",
    "Q2 report",
    "Q3 report",
    "Q4 report",
    "interim report",
    "interim financial statements",
    "half-year report",
    "half yearly report",
    "half-yearly financial statements",
    "first quarter",
    "second quarter",
    "third quarter",
    "fourth quarter",
]

# ==========================================================================
# TIER 3 — REGULATORY & MARKET-SPECIFIC FILINGS
# ==========================================================================
TIER_3_REGULATORY = [
    # SEC Filings (US)
    "Form 10-K",
    "10-K",
    "10-K/A",
    "Form 10-Q",
    "10-Q",
    "8-K",
    "20-F",
    "40-F",
    "SEC filings",
    "SEC reports",
    "EDGAR filing",
    "annual SEC filing",
    
    # International Standards
    "IFRS financial statements",
    "regulated information",
    "regulated disclosures",
    "directors report",
    "strategic report",
    "management report",
    "corporate filings",
    
    # UK/EU specific
    "annual return",
    "accounts filed",
    "companies house",
]

# ==========================================================================
# TIER 4 — INVESTOR RELATIONS & NAVIGATION TERMS
# ==========================================================================
TIER_4_INVESTOR_RELATIONS = [
    "investor relations",
    "investors",
    "IR",
    "investor information",
    "investor centre",
    "investor center",
    "investor resources",
    "investor downloads",
    "financials",
    "reports and presentations",
    "results and reports",
    "presentations",
    "downloads",
    "documents",
    "filings",
    "disclosures",
    "shareholder information",
    "stockholder information",
]

# ==========================================================================
# TIER 5 — ACCOUNTING & AUDIT TERMINOLOGY
# ==========================================================================
TIER_5_ACCOUNTING = [
    "audited accounts",
    "unaudited accounts",
    "management accounts",
    "statement of financial position",
    "statement of profit and loss",
    "profit and loss statement",
    "income statement",
    "balance sheet",
    "cash flow statement",
    "statement of cash flows",
    "notes to the financial statements",
    "financial notes",
    "accounts summary",
    "comprehensive income",
    "equity statement",
    "statement of changes in equity",
]

# ==========================================================================
# TIER 6 — FILE FORMAT, FILE NAME & PATTERN MATCHING
# ==========================================================================
TIER_6_FILE_PATTERNS = [
    # File type indicators
    "filetype:pdf",
    ".pdf",
    
    # Common file names
    "annual-report.pdf",
    "annual_report.pdf",
    "financial-statements.pdf",
    "financials.pdf",
    "results.pdf",
    "form-10k.pdf",
    "form10k.pdf",
    "20f.pdf",
    "FY.pdf",
    "annual-results.pdf",
    "quarterly-report.pdf",
]

# Year pattern regex for matching financial years
YEAR_PATTERNS = [
    r'(19|20)[0-9]{2}',           # Basic year: 2023, 2024
    r'FY(19|20)[0-9]{2}',         # Fiscal year: FY2023
    r'Q[1-4][-_]?(19|20)[0-9]{2}', # Quarter: Q1_2023, Q1-2023
    r'(19|20)[0-9]{2}[-_]Q[1-4]', # Year-Quarter: 2023-Q1
    r'H[1-2][-_]?(19|20)[0-9]{2}', # Half year: H1_2023
]

YEAR_PATTERN_COMBINED = re.compile(r'|'.join(YEAR_PATTERNS), re.IGNORECASE)

# ==========================================================================
# TIER 7 — COMMON URL PATH & DIRECTORY INDICATORS
# ==========================================================================
TIER_7_URL_PATHS = [
    "/investors/",
    "/investor-relations/",
    "/investor/",
    "/financials/",
    "/reports/",
    "/results/",
    "/documents/",
    "/downloads/",
    "/filings/",
    "/disclosures/",
    "/media/",
    "/publications/",
    "/annual-reports/",
    "/quarterly-reports/",
    "/sec-filings/",
    "/regulatory/",
    "/governance/",
    "/ir/",
]

# ==========================================================================
# TIER 8 — NON-ENGLISH HIGH-VALUE FINANCIAL TERMS
# ==========================================================================
TIER_8_MULTILINGUAL = {
    "spanish": [
        "informe anual",
        "estados financieros",
        "resultados financieros",
        "demostraciones financieras",
        "memoria anual",
        "cuentas anuales",
        "informe de gestión",
    ],
    "portuguese": [
        "relatório anual",
        "informações financeiras",
        "demonstrações financeiras",
        "balanço patrimonial",
        "relatório de administração",
    ],
    "french": [
        "rapport annuel",
        "états financiers",
        "informations financières",
        "rapport financier",
        "comptes annuels",
        "bilan financier",
        "rapport de gestion",
    ],
    "german": [
        "geschäftsbericht",
        "jahresbericht",
        "finanzbericht",
        "abschluss",
        "konzernabschluss",
        "jahresabschluss",
        "bilanz",
        "quartalsbericht",
    ],
    "italian": [
        "bilancio",
        "bilancio annuale",
        "relazione finanziaria",
        "relazione annuale",
        "conto economico",
        "rendiconto finanziario",
    ],
    "dutch": [
        "jaarverslag",
        "financieel verslag",
        "jaarrekening",
        "kwartaalverslag",
        "halfjaarverslag",
    ],
    "chinese_simplified": [
        "年度报告",
        "财务报告",
        "中期报告",
        "财务报表",
        "年报",
        "季度报告",
        "财务信息",
    ],
    "chinese_traditional": [
        "年度報告",
        "財務報告",
        "中期報告",
        "財務報表",
        "年報",
        "季度報告",
    ],
    "japanese": [
        "有価証券報告書",
        "決算報告書",
        "財務諸表",
        "年次報告書",
        "四半期報告書",
        "事業報告",
    ],
    "korean": [
        "사업보고서",
        "재무제표",
        "분기보고서",
        "반기보고서",
        "연차보고서",
        "감사보고서",
    ],
}

# ==========================================================================
# AGGREGATED KEYWORD SETS FOR EASY ACCESS
# ==========================================================================

def get_all_english_keywords() -> Set[str]:
    """Get all English keywords from tiers 1-5."""
    keywords = set()
    keywords.update(TIER_1_UNIVERSAL)
    keywords.update(TIER_2_PERIODIC)
    keywords.update(TIER_3_REGULATORY)
    keywords.update(TIER_4_INVESTOR_RELATIONS)
    keywords.update(TIER_5_ACCOUNTING)
    return keywords

def get_all_multilingual_keywords() -> Set[str]:
    """Get all non-English keywords from tier 8."""
    keywords = set()
    for lang_keywords in TIER_8_MULTILINGUAL.values():
        keywords.update(lang_keywords)
    return keywords

def get_all_keywords() -> Set[str]:
    """Get all keywords across all tiers and languages."""
    keywords = get_all_english_keywords()
    keywords.update(get_all_multilingual_keywords())
    return keywords

def get_url_path_patterns() -> List[str]:
    """Get URL path patterns for investor relations pages."""
    return TIER_7_URL_PATHS.copy()

def get_file_patterns() -> List[str]:
    """Get common file name patterns."""
    return TIER_6_FILE_PATTERNS.copy()

# ==========================================================================
# DOCUMENT TYPE DETECTION
# ==========================================================================

DOCUMENT_TYPE_KEYWORDS = {
    "annual_report": [
        "annual report", "10-k", "form 10-k", "yearly report", "year-end report",
        "annual financial", "geschäftsbericht", "rapport annuel", "informe anual",
        "年度报告", "年報", "年次報告書", "연차보고서"
    ],
    "quarterly_report": [
        "quarterly report", "10-q", "form 10-q", "q1", "q2", "q3", "q4",
        "first quarter", "second quarter", "third quarter", "fourth quarter",
        "quartalsbericht", "四半期報告書", "분기보고서", "季度报告"
    ],
    "interim_report": [
        "interim report", "half-year", "half year", "h1", "h2", "semi-annual",
        "halbjahresbericht", "中期报告", "반기보고서"
    ],
    "10k": ["10-k", "form 10-k", "10k"],
    "10q": ["10-q", "form 10-q", "10q"],
    "20f": ["20-f", "form 20-f", "20f"],
    "8k": ["8-k", "form 8-k", "8k", "current report"],
    "financial_statements": [
        "financial statements", "audited financial", "consolidated financial",
        "financial position", "income statement", "balance sheet"
    ],
    "earnings_release": [
        "earnings release", "earnings report", "earnings announcement",
        "results announcement", "financial results"
    ],
    "investor_presentation": [
        "investor presentation", "presentation", "investor deck", "slides"
    ],
}

def detect_document_type(text: str) -> str:
    """
    Detect document type from text (title, URL, or content).
    
    Args:
        text: Text to analyze
        
    Returns:
        Document type string (e.g., 'annual_report', '10k', etc.)
    """
    text_lower = text.lower()
    
    # Check each document type in priority order
    for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return doc_type
    
    return "financial_document"  # Default fallback

# ==========================================================================
# LANGUAGE DETECTION & ENGLISH-FIRST PREFERENCE
# ==========================================================================

# URL patterns that indicate English version
ENGLISH_URL_INDICATORS = [
    '/en/',
    '/eng/',
    '/english/',
    '-en.',
    '-en/',
    '_en.',
    '_en/',
    '-eng.',
    '-english.',
    '/en-',
    '/en_',
    'lang=en',
    'language=en',
    'locale=en',
]

# URL patterns that indicate non-English versions
NON_ENGLISH_URL_INDICATORS = {
    'russian': ['/ru/', '-ru.', '_ru.', '/russian/', 'lang=ru'],
    'german': ['/de/', '-de.', '_de.', '/german/', 'lang=de'],
    'french': ['/fr/', '-fr.', '_fr.', '/french/', 'lang=fr'],
    'spanish': ['/es/', '-es.', '_es.', '/spanish/', 'lang=es'],
    'portuguese': ['/pt/', '-pt.', '_pt.', '/portuguese/', 'lang=pt'],
    'italian': ['/it/', '-it.', '_it.', '/italian/', 'lang=it'],
    'dutch': ['/nl/', '-nl.', '_nl.', '/dutch/', 'lang=nl'],
    'chinese': ['/cn/', '/zh/', '-cn.', '-zh.', '/chinese/', 'lang=zh'],
    'japanese': ['/ja/', '/jp/', '-ja.', '-jp.', '/japanese/', 'lang=ja'],
    'korean': ['/ko/', '/kr/', '-ko.', '-kr.', '/korean/', 'lang=ko'],
}

LANGUAGE_INDICATORS = {
    "english": ["annual report", "financial statements", "quarterly report", "investor relations"],
    "spanish": ["informe anual", "estados financieros"],
    "portuguese": ["relatório anual", "demonstrações financeiras"],
    "french": ["rapport annuel", "états financiers"],
    "german": ["geschäftsbericht", "jahresbericht"],
    "italian": ["bilancio", "relazione finanziaria"],
    "dutch": ["jaarverslag", "financieel verslag"],
    "russian": ["годовой отчет", "финансовая отчетность", "годовая отчетность"],
    "chinese": ["年度报告", "财务报告", "年報", "財務報告"],
    "japanese": ["有価証券報告書", "決算報告書"],
    "korean": ["사업보고서", "재무제표"],
}

def detect_language_from_url(url: str) -> str:
    """
    Detect language from URL patterns.
    
    Args:
        url: URL to analyze
        
    Returns:
        Language code or None if not detected
    """
    url_lower = url.lower()
    
    # Check for English indicators first
    for indicator in ENGLISH_URL_INDICATORS:
        if indicator in url_lower:
            return "english"
    
    # Check for non-English indicators
    for language, indicators in NON_ENGLISH_URL_INDICATORS.items():
        for indicator in indicators:
            if indicator in url_lower:
                return language
    
    return None

def detect_language(text: str, url: str = "") -> str:
    """
    Detect language from text and URL based on financial term indicators.
    
    Args:
        text: Text to analyze (title, content)
        url: URL to analyze for language patterns
        
    Returns:
        Language code (e.g., 'english', 'german', etc.)
    """
    # First check URL for language indicators
    if url:
        url_lang = detect_language_from_url(url)
        if url_lang:
            return url_lang
    
    text_lower = text.lower()
    
    # Check text content for language indicators
    for language, indicators in LANGUAGE_INDICATORS.items():
        for indicator in indicators:
            if indicator.lower() in text_lower:
                return language
    
    return "english"  # Default to English

def is_english_version(url: str, title: str = "") -> bool:
    """
    Check if a document appears to be the English version.
    
    Args:
        url: Document URL
        title: Document title
        
    Returns:
        True if likely English version
    """
    url_lower = url.lower()
    title_lower = title.lower() if title else ""
    
    # Check for explicit English indicators
    for indicator in ENGLISH_URL_INDICATORS:
        if indicator in url_lower:
            return True
    
    # Check title for English keywords
    english_title_indicators = ['english', '(en)', '[en]', 'en version']
    for indicator in english_title_indicators:
        if indicator in title_lower:
            return True
    
    # If no non-English indicators found, assume English
    for lang, indicators in NON_ENGLISH_URL_INDICATORS.items():
        for indicator in indicators:
            if indicator in url_lower:
                return False
    
    return True  # Default: assume English if no indicators

def get_language_preference_note(language: str, english_available: bool) -> str:
    """
    Generate a note about language preference for the document.
    
    Args:
        language: Detected language
        english_available: Whether English version was found
        
    Returns:
        Note string for the document
    """
    if language == "english":
        return "English version"
    elif english_available:
        return f"English version available; returning {language} as requested"
    else:
        return f"English version not found; returning official {language} original"


# ==========================================================================
# CONFIDENCE SCORING
# ==========================================================================

def calculate_confidence_score(
    has_pdf: bool,
    has_year: bool,
    tier_matches: Dict[int, int],
    has_url_path_match: bool = False
) -> float:
    """
    Calculate confidence score based on matches.
    
    Ranking (from specification):
    - Highest: annual report + pdf + year
    - High: financial statements + pdf
    - Medium: results / presentation + pdf
    
    Args:
        has_pdf: Whether the URL points to a PDF
        has_year: Whether a year was detected
        tier_matches: Dict of tier number to count of matches
        has_url_path_match: Whether URL matches investor relations path
        
    Returns:
        Confidence score from 0.0 to 1.0
    """
    score = 0.0
    
    # Base score for PDF
    if has_pdf:
        score += 0.3
    
    # Year detection adds confidence
    if has_year:
        score += 0.2
    
    # URL path match adds confidence
    if has_url_path_match:
        score += 0.1
    
    # Tier-based scoring (higher tiers = higher priority)
    tier_weights = {
        1: 0.25,  # Universal terms - highest weight
        2: 0.20,  # Periodic terms
        3: 0.18,  # Regulatory terms
        4: 0.12,  # IR navigation
        5: 0.10,  # Accounting terms
        6: 0.05,  # File patterns
        7: 0.05,  # URL paths
        8: 0.15,  # Multilingual (important for global coverage)
    }
    
    for tier, count in tier_matches.items():
        if tier in tier_weights and count > 0:
            score += tier_weights[tier] * min(count, 3) / 3  # Cap at 3 matches
    
    return min(score, 1.0)

# ==========================================================================
# SEARCH QUERY BUILDERS
# ==========================================================================

def build_comprehensive_search_queries(
    company: str,
    year: int = None,
    report_type: str = "annual"
) -> List[str]:
    """
    Build multiple search queries for comprehensive document discovery.
    
    Args:
        company: Company name or ticker
        year: Optional year filter
        report_type: Type of report to search for
        
    Returns:
        List of search query strings
    """
    queries = []
    year_str = str(year) if year else ""
    
    # Query templates based on report type
    if report_type in ["annual", "10-k"]:
        base_terms = ["annual report", "10-K", "financial statements", "annual filing"]
    elif report_type in ["quarterly", "10-q"]:
        base_terms = ["quarterly report", "10-Q", "quarterly results", "Q1 Q2 Q3 Q4"]
    elif report_type == "interim":
        base_terms = ["interim report", "half-year report", "semi-annual"]
    else:
        base_terms = ["financial statements", "investor relations", "financial report"]
    
    # Build queries with different combinations
    for term in base_terms:
        # Basic query
        query = f"{company} {term}"
        if year_str:
            query += f" {year_str}"
        query += " filetype:pdf"
        queries.append(query)
    
    # Add investor relations page query
    queries.append(f"{company} investor relations reports")
    
    # Add SEC-specific query for US companies
    if report_type in ["annual", "10-k"]:
        queries.append(f"{company} SEC 10-K filing {year_str} site:sec.gov")
    
    return queries

def extract_year_from_text(text: str) -> int:
    """
    Extract year from text using year patterns.
    
    Args:
        text: Text to search for year
        
    Returns:
        Year as integer, or None if not found
    """
    # Try to find FY pattern first (more specific)
    fy_match = re.search(r'FY\s*(20[0-9]{2}|19[0-9]{2})', text, re.IGNORECASE)
    if fy_match:
        return int(fy_match.group(1))
    
    # Try basic year pattern
    year_match = re.search(r'\b(20[0-9]{2}|19[8-9][0-9])\b', text)
    if year_match:
        return int(year_match.group(1))
    
    return None


# For easy import
TIER_KEYWORDS = {
    1: TIER_1_UNIVERSAL,
    2: TIER_2_PERIODIC,
    3: TIER_3_REGULATORY,
    4: TIER_4_INVESTOR_RELATIONS,
    5: TIER_5_ACCOUNTING,
    6: TIER_6_FILE_PATTERNS,
    7: TIER_7_URL_PATHS,
    8: TIER_8_MULTILINGUAL,
}


if __name__ == "__main__":
    # Test the module
    print(f"Total English keywords: {len(get_all_english_keywords())}")
    print(f"Total multilingual keywords: {len(get_all_multilingual_keywords())}")
    print(f"Total keywords: {len(get_all_keywords())}")
    print(f"\nURL path patterns: {len(get_url_path_patterns())}")
    print(f"File patterns: {len(get_file_patterns())}")
    
    # Test document type detection
    test_texts = [
        "Apple Inc Annual Report 2024.pdf",
        "Form 10-K for fiscal year 2023",
        "Q3 Quarterly Results",
        "Geschäftsbericht 2024",
    ]
    
    print("\nDocument type detection tests:")
    for text in test_texts:
        doc_type = detect_document_type(text)
        lang = detect_language(text)
        print(f"  '{text[:40]}...' -> {doc_type} ({lang})")
