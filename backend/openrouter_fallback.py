"""
OpenRouter ChatGPT Fallback Retriever

Enhanced retriever that uses OpenRouter (ChatGPT/Claude) for comprehensive
financial document discovery using 8-tier keyword matching for MAXIMUM RECALL.
"""

import os
import re
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)


# ============================================
# COMPREHENSIVE DOCUMENT DISCOVERY PROMPT
# Maximum Recall with 8-Tier Keyword System
# ============================================

DOCUMENT_DISCOVERY_PROMPT = """You are an automated financial document discovery agent with MAXIMUM RECALL requirements.

TASK: Find investor documents for:
- Company: {company}
- Years: {start_year} to {end_year}
- Document types: {doc_types}

=== DOCUMENT TYPES TO FIND (ALL CRITICAL) ===

1. ANNUAL REPORTS: annual report, annual financial statements, statutory accounts, 10-K, 20-F
2. QUARTERLY REPORTS: quarterly report, interim report, Q1/Q2/Q3/Q4 results, 10-Q, half-year report
3. EARNINGS RELEASES: earnings release, press release (results), results announcement, trading update
4. PRESENTATIONS: investor presentation, earnings deck, results presentation

=== 8-TIER KEYWORD MATCHING ===

TIER 1 (UNIVERSAL): financial statements, annual report, financial results, financial disclosure
TIER 2 (ANNUAL/QUARTERLY): yearly report, quarterly report, interim report, H1/H2 report, 9M results
TIER 3 (REGULATORY): 10-K, 10-Q, 8-K, 6-K, 20-F, 40-F, SEC filings, IFRS statements
TIER 4 (IR NAVIGATION): reports and presentations, earnings releases, results centre, announcements, filings
TIER 5 (ACCOUNTING): audited accounts, consolidated statements, balance sheet, income statement
TIER 6 (FILENAMES): annual-report.pdf, earnings-release.pdf, quarterly-report.pdf, Q1-results.pdf
TIER 7 (URL PATHS): /investors/, /results/, /earnings/, /press-releases/, /reports-and-presentations/
TIER 8 (MULTILINGUAL): informe anual, rapport annuel, Geschäftsbericht, faaliyet raporu, 年度报告

=== MANDATORY RETRIEVAL STEPS ===

STEP 1: FIND OFFICIAL COMPANY DOMAIN
- Identify verified company website (NOT third-party, NOT SEC-only)

STEP 2: FIND ALL REPORTS PAGES (MUST find deep pages, not just /investors/)
- Annual reports page
- Quarterly/Interim results page
- Earnings releases / Press releases page
- Investor presentations page
- Filings/Disclosures page

STEP 3: EXTRACT ALL PDFs
- Annual reports, quarterly reports, earnings releases, presentations
- Include ALL years available, not just requested years

STEP 4: IF NO PDFs FOUND
- Explain which pages were checked
- Return the deepest reports page URLs found

=== OUTPUT CONTRACT (MANDATORY JSON) ===

{{
  "company": "{company}",
  "official_website": "https://www.company.com",
  "official_investor_relations": "https://www.company.com/investors",
  "reports_pages": [
    {{"doc_category": "Annual", "url": "https://company.com/investors/annual-reports"}},
    {{"doc_category": "Quarterly", "url": "https://company.com/investors/quarterly-results"}},
    {{"doc_category": "Earnings", "url": "https://company.com/investors/earnings-releases"}},
    {{"doc_category": "Presentations", "url": "https://company.com/investors/presentations"}},
    {{"doc_category": "Filings", "url": "https://company.com/investors/filings"}}
  ],
  "documents": [
    {{
      "title": "Annual Report 2023",
      "doc_type": "annual_report",
      "period": "FY2023",
      "pdf_url": "https://direct-link.pdf",
      "source_page": "https://page-where-found"
    }},
    {{
      "title": "Q2 2024 Earnings Release",
      "doc_type": "earnings_release",
      "period": "Q2 2024",
      "pdf_url": "https://earnings-release.pdf",
      "source_page": "https://earnings-page"
    }},
    {{
      "title": "Q3 2024 Investor Presentation",
      "doc_type": "presentation",
      "period": "Q3 2024",
      "pdf_url": "https://presentation.pdf",
      "source_page": "https://presentations-page"
    }}
  ],
  "notes": "Checked [list pages]. Found [X] documents. [Explain any issues]."
}}

=== CRITICAL RULES ===

1. MAXIMUM RECALL: Favor over-inclusion. Better to return extra results than miss a document.
2. Return ALL document types: annual, quarterly, earnings releases, presentations
3. reports_pages must be DEEP pages (not homepage, not generic IR)
4. If documents is empty, notes MUST explain which pages were checked
5. Only return PDFs from official company domain or regulators
6. Do NOT return third-party analyst reports

DO NOT include any text outside the JSON. Return ONLY the JSON."""


class OpenRouterFallbackRetriever:
    """
    Fallback retriever using OpenRouter (ChatGPT/Claude) with web browsing.
    
    Triggered when Serper/Tavily return 0 valid documents.
    Uses LLM's knowledge and reasoning to find investor documents.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize the OpenRouter fallback retriever.
        
        Args:
            api_key: OpenRouter API key
            model: Model to use (default: openai/gpt-4o)
            base_url: OpenRouter API base URL
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
        self.base_url = base_url
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required for fallback retrieval")
        
        if not OpenAI:
            raise ImportError("openai package is required. Install with: pip install openai")
        
        # Initialize OpenAI client with OpenRouter base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        logger.info(f"OpenRouter fallback initialized with model: {self.model}")
    
    def retrieve_documents(
        self,
        company: str,
        doc_types: List[str],
        start_year: int,
        end_year: int,
    ) -> Dict:
        """
        Use ChatGPT to find investor documents when other methods fail.
        
        Args:
            company: Company name or ticker
            doc_types: List of document types to find
            start_year: Start year
            end_year: End year
            
        Returns:
            Dict with 'documents' list and metadata
        """
        logger.info(f"OpenRouter fallback: Searching for {company} documents ({start_year}-{end_year})")
        
        # Format document types for the prompt
        doc_types_str = ", ".join(doc_types) if doc_types else "annual reports, financial statements"
        
        # Build the prompt
        prompt = DOCUMENT_DISCOVERY_PROMPT.format(
            company=company,
            doc_types=doc_types_str,
            start_year=start_year,
            end_year=end_year,
        )
        
        try:
            # Call OpenRouter API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial document research assistant. You help find official investor reports and financial documents from company websites. Always return valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent, factual responses
                max_tokens=2000,
            )
            
            # Extract response content
            content = response.choices[0].message.content
            logger.debug(f"OpenRouter raw response: {content[:500]}...")
            
            # Parse JSON response
            result = self._parse_response(content)
            
            # Validate and filter documents
            valid_docs = self._validate_documents(result.get('documents', []), start_year, end_year)
            
            return {
                'company': result.get('company', company),
                'official_website': result.get('official_website', ''),
                'official_investor_relations': result.get('official_investor_relations', ''),
                'reports_pages': result.get('reports_pages', []),
                'documents': valid_docs,
                'notes': result.get('notes', ''),
                'source': 'openrouter_fallback',
                'model': self.model,
            }
            
        except Exception as e:
            logger.error(f"OpenRouter fallback failed: {e}")
            return {
                'company': company,
                'official_website': '',
                'official_investor_relations': '',
                'reports_pages': [],
                'documents': [],
                'notes': f"OpenRouter fallback error: {str(e)}",
                'source': 'openrouter_fallback',
                'error': str(e),
            }
    
    def _parse_response(self, content: str) -> Dict:
        """Parse the JSON response from the LLM."""
        # Clean up the response - remove markdown code blocks if present
        content = content.strip()
        
        # Remove markdown JSON code blocks
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        
        if content.endswith('```'):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            return {'documents': [], 'search_notes': 'Failed to parse response'}
    
    def _validate_documents(self, documents: List[Dict], start_year: int, end_year: int) -> List[Dict]:
        """Validate and filter documents."""
        valid_docs = []
        
        for doc in documents:
            # Must have pdf_url
            pdf_url = doc.get('pdf_url', '')
            if not pdf_url:
                continue
            
            # Validate it looks like a PDF URL
            if not self._is_valid_pdf_url(pdf_url):
                logger.debug(f"Skipping non-PDF URL: {pdf_url}")
                continue
            
            # Try to extract year from period
            period = doc.get('period', '')
            year_match = re.search(r'(20\d{2})', period)
            if year_match:
                year = int(year_match.group(1))
                if not (start_year <= year <= end_year):
                    logger.debug(f"Skipping document outside year range: {period}")
                    continue
            
            # Clean up and normalize the document
            valid_doc = {
                'title': doc.get('title', 'Financial Document'),
                'doc_type': self._normalize_doc_type(doc.get('doc_type', 'annual_report')),
                'period': period,
                'pdf_url': pdf_url,
                'source_page': doc.get('source_page', ''),
            }
            
            valid_docs.append(valid_doc)
        
        logger.info(f"OpenRouter fallback: Validated {len(valid_docs)} documents")
        return valid_docs
    
    def _is_valid_pdf_url(self, url: str) -> bool:
        """Check if URL looks like a valid PDF link."""
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Must start with http/https
        if not url_lower.startswith('http'):
            return False
        
        # Check for PDF indicators
        if '.pdf' in url_lower:
            return True
        
        # Some download URLs don't have .pdf in path
        if 'download' in url_lower and ('report' in url_lower or 'annual' in url_lower):
            return True
        
        return False
    
    def _normalize_doc_type(self, doc_type: str) -> str:
        """Normalize document type string."""
        doc_type_lower = doc_type.lower().replace(' ', '_').replace('-', '_')
        
        type_mapping = {
            'annual': 'annual_report',
            'annual_report': 'annual_report',
            '10_k': '10-K',
            '10k': '10-K',
            '10_q': '10-Q',
            '10q': '10-Q',
            '20_f': '20-F',
            '20f': '20-F',
            'quarterly': 'quarterly_report',
            'quarterly_report': 'quarterly_report',
            'earnings': 'earnings_release',
            'earnings_release': 'earnings_release',
            'financial_statements': 'financial_statements',
            'interim': 'interim_report',
        }
        
        return type_mapping.get(doc_type_lower, doc_type)


def test_openrouter_fallback():
    """Test the OpenRouter fallback retriever."""
    print("=" * 60)
    print("Testing OpenRouter Fallback Retriever")
    print("=" * 60)
    
    try:
        retriever = OpenRouterFallbackRetriever()
        
        result = retriever.retrieve_documents(
            company="Apple Inc",
            doc_types=["annual report", "10-K"],
            start_year=2023,
            end_year=2024,
        )
        
        print(f"\nResults:")
        print(f"  Documents found: {len(result.get('documents', []))}")
        print(f"  IR Page: {result.get('ir_reports_page')}")
        print(f"  Notes: {result.get('search_notes')}")
        
        for doc in result.get('documents', [])[:3]:
            print(f"\n  📄 {doc['title']}")
            print(f"     Type: {doc['doc_type']}")
            print(f"     Period: {doc['period']}")
            print(f"     URL: {doc['pdf_url'][:60]}...")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_openrouter_fallback()
