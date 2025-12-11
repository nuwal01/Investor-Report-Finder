"""
OpenAI + Serper Hybrid Report Finder

Uses OpenAI for intelligent query parsing and Serper API for web search.
This replicates ChatGPT's web browsing capability.
"""

import os
import re
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class OpenAISerperReportFinder:
    """
    Find investor relations reports using OpenAI (parsing) + Serper (web search).
    """
    
    def __init__(self, openai_key: Optional[str] = None, serper_key: Optional[str] = None):
        """
        Initialize the hybrid report finder.
        
        Args:
            openai_key: OpenAI API key (optional, uses env var if not provided)
            serper_key: Serper API key (optional, uses env var if not provided)
        """
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.serper_key = serper_key or os.getenv("SERPER_API_KEY")
        
        if not self.serper_key:
            raise ValueError("Serper API key is required. Get one free at https://serper.dev (2,500 searches/month)")
        
        # Try to initialize OpenAI (for parsing)
        self.openai_client = None
        if self.openai_key and OpenAI:
            try:
                self.openai_client = OpenAI(api_key=self.openai_key)
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI: {e}")
                print("Will use fallback regex parsing")
    
    def find_reports(self, prompt: str) -> List[Dict]:
        """
        Find investor reports using OpenAI + Serper.
        
        Args:
            prompt: Natural language query (e.g., "Financial statements of Turkcell TCELL")
        
        Returns:
            List of report dictionaries with year, type, title, url
        """
        print(f"\n{'='*60}")
        print(f"Processing prompt: {prompt}")
        print(f"{'='*60}")
        
        # Step 1: Parse query with OpenAI (or fallback to regex)
        parsed = self._parse_query(prompt)
        print(f"\nParsed query:")
        print(f"  Company: {parsed.get('company')}")
        print(f"  Report Type: {parsed.get('report_type')}")
        print(f"  Years: {parsed.get('years')}")
        
        if not parsed.get('company'):
            raise ValueError("Could not identify company from prompt")
        
        # Step 2: Search for PDFs using Serper
        reports = self._search_with_serper(
            company=parsed['company'],
            report_type=parsed.get('report_type', 'annual'),
            years=parsed.get('years', [datetime.now().year])
        )
        
        # Step 3: ALWAYS add investor relations page at the end (not just as fallback)
        ir_page = self._find_investor_relations_page(parsed['company'])
        if ir_page:
            reports.append({
                'year': parsed.get('years', [datetime.now().year])[-1],  # Use latest year
                'type': 'investor_relations_page',
                'title': f"{parsed['company']} - Investor Relations (Official Source)",
                'url': ir_page,
                'source': 'serper'
            })
            print(f"\n📌 Added official investor relations page: {ir_page}")
        
        print(f"\n✅ FINAL RESULTS: Found {len(reports)} total results for '{parsed['company']}'")
        print(f"   Requested company: {parsed['company']}")
        print(f"   Report type: {parsed.get('report_type', 'annual')}")
        print(f"   Years: {parsed.get('years', [datetime.now().year])}")
        return reports
    
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

Respond in JSON:
{
  "company": "company name or ticker",
  "report_type": "annual|quarterly|10-k|10-q|earnings|financial_statements",
  "years": [2020, 2021, 2022]
}

If no years specified, use current year. If no report type, use "annual"."""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _parse_with_regex(self, prompt: str) -> Dict:
        """Fallback parser using regex patterns."""
        # Extract years
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
        
        # Extract report type
        report_type = 'annual'
        prompt_lower = prompt.lower()
        if 'quarterly' in prompt_lower:
            report_type = 'quarterly'
        elif '10-k' in prompt_lower:
            report_type = '10-k'
        elif '10-q' in prompt_lower:
            report_type = '10-q'
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
            'years': years
        }
    
    def _search_with_serper(self, company: str, report_type: str, years: List[int]) -> List[Dict]:
        """
        Search for reports using Serper API (Google search).
        
        This replicates what ChatGPT does with its web browsing feature.
        """
        all_reports = []
        
        for year in years:
            # Construct search query (similar to what ChatGPT would do)
            search_queries = [
                f"{company} {report_type} {year} investor relations PDF",
                f"{company} annual report {year} PDF site:investor",
                f"{company} {year} 10-K PDF filetype:pdf"
            ]
            
            for query in search_queries:
                print(f"\nSearching: {query}")
                
                try:
                    # Call Serper API
                    response = requests.post(
                        'https://google.serper.dev/search',
                        headers={
                            'X-API-KEY': self.serper_key,
                            'Content-Type': 'application/json'
                        },
                        json={
                            'q': query,
                            'num': 10  # Get top 10 results
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        results = response.json()
                        
                        # Extract PDF URLs from results
                        pdf_urls = self._extract_pdf_urls(results, year, report_type, company)
                        
                        if pdf_urls:
                            all_reports.extend(pdf_urls)
                            break  # Found PDFs for this year, move to next
                
                except Exception as e:
                    print(f"Serper search error: {e}")
                    continue
        
        # Deduplicate by year+URL combination to avoid duplicate years
        seen_combinations = set()
        unique_reports = []
        for report in all_reports:
            # Create a unique key combining year and URL
            key = (report['year'], report['url'])
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_reports.append(report)
        
        return unique_reports
    
    def _extract_pdf_urls(self, serper_results: Dict, year: int, report_type: str, company: str) -> List[Dict]:
        """Extract PDF URLs from Serper search results with strict type filtering."""
        pdf_reports = []
        
        # Define keywords for each report type
        quarterly_keywords = ['q1', 'q2', 'q3', 'q4', 'quarter', 'quarterly', '1q', '2q', '3q', '4q']
        annual_keywords = ['annual', '10-k', 'form 10-k', 'yearly', 'form 20-f']
        exclude_keywords = ['sustainability', 'presentation', 'investor presentation', 'riding', 'wave', 'esg', 'corporate social']
        
        # Check organic results
        for result in serper_results.get('organic', []):
            link = result.get('link', '')
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()
            
            # Check if it's a PDF link
            if '.pdf' in link.lower() or 'pdf' in title:
                if not self._validate_pdf_url(link):
                    continue
                
                # STRICT FILTERING: Check if title/snippet matches requested report type
                if report_type == 'quarterly':
                    # Must contain quarterly keywords
                    has_quarterly = any(kw in title or kw in snippet for kw in quarterly_keywords)
                    # Must NOT be annual or excluded type
                    is_annual = any(kw in title for kw in annual_keywords if kw not in quarterly_keywords)
                    is_excluded = any(kw in title for kw in exclude_keywords)
                    
                    if not has_quarterly or is_annual or is_excluded:
                        print(f"  ❌ Filtered out (not quarterly): {title[:50]}")
                        continue
                        
                elif report_type in ['annual', '10-k']:
                    # Must contain annual keywords
                    has_annual = any(kw in title or kw in snippet for kw in annual_keywords)
                    # Must NOT be quarterly or excluded type
                    is_quarterly = any(kw in title for kw in quarterly_keywords)
                    is_excluded = any(kw in title for kw in exclude_keywords)
                    
                    if not has_annual or is_quarterly or is_excluded:
                        print(f"  ❌ Filtered out (not annual): {title[:50]}")
                        continue
                
                # STRICT: Check company name is actually in the result
                company_lower = company.lower()
                # Extract main company name (remove ticker if present)
                company_main = re.sub(r'\s*\([^)]*\)', '', company_lower).strip()
                company_words = company_main.split()
                
                # Filter out common business words that don't help identify the company
                common_words = ['inc', 'corp', 'corporation', 'ltd', 'limited', 'co', 'company', 
                               'the', 'and', 'of', 'group', 'holdings', 'international']
                significant_words = [word for word in company_words if len(word) > 3 and word not in common_words]
                
                # Require ALL significant company words to appear in title or URL
                if significant_words:
                    matches = []
                    for word in significant_words:
                        if word in title or word in link.lower():
                            matches.append(word)
                    
                    # Must match ALL significant words (strict validation)
                    if len(matches) != len(significant_words):
                        print(f"  ❌ Filtered out (company mismatch): {title[:50]}")
                        print(f"     Expected ALL words: {significant_words}, Found only: {matches}")
                        continue
                else:
                    # If no significant words, fall back to checking any company word
                    has_company = False
                    for word in company_words:
                        if len(word) > 2:  # Skip very short words
                            if word in title or word in link.lower():
                                has_company = True
                                break
                    
                    if not has_company:
                        print(f"  ❌ Filtered out (company mismatch): {title[:50]}")
                        continue
                
                # STRICT: Check year is actually in title or URL
                year_str = str(year)
                if year_str not in title and year_str not in link:
                    print(f"  ❌ Filtered out (year mismatch - expected {year}): {title[:50]}")
                    continue
                
                print(f"  ✅ Matched: {title[:60]}")
                pdf_reports.append({
                    'year': year,
                    'type': report_type,
                    'title': result.get('title', ''),
                    'url': link,
                    'source': 'serper'
                })
        
        return pdf_reports
    
    def _find_investor_relations_page(self, company: str) -> Optional[str]:
        """
        Find the company's investor relations page URL.
        Returns the IR page as a fallback when PDFs aren't found.
        """
        try:
            # Search for investor relations page
            query = f"{company} investor relations"
            print(f"\n🔎 Searching for IR page: {query}")
            
            response = requests.post(
                'https://google.serper.dev/search',
                headers={
                    'X-API-KEY': self.serper_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'q': query,
                    'num': 5
                },
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                
                # Look for official IR page
                for result in results.get('organic', []):
                    link = result.get('link', '')
                    title = result.get('title', '').lower()
                    
                    # Check if it's an investor relations page
                    if ('investor' in link.lower() or 'ir.' in link.lower() or 
                        'investor' in title or 'annual' in title):
                        # Exclude PDF files
                        if not link.endswith('.pdf'):
                            return link
            
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
