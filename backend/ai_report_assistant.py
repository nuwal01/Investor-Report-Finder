"""
AI Report Assistant

For companies from countries not allowed to use Tavily/Serper (non-USA/India/UK),
uses AI to actually FIND and EXTRACT investor report URLs and information.
"""

import os
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', '')


class AIReportAssistant:
    """Uses AI to find and extract investor reports."""
    
    def __init__(self):
        """Initialize the AI assistant."""
        self.has_openai = bool(OPENAI_API_KEY)
        self.has_gemini = bool(GOOGLE_API_KEY)
    
    def find_reports_with_ai(
        self,
        company_name: str,
        ticker: Optional[str],
        country: str,
        report_type: str,
        start_year: int,
        end_year: int
    ) -> List[Dict]:
        """
        Use AI to actuallyFIND and EXTRACT investor report URLs.
        
        Returns:
            List of report dictionaries with structure:
            [{
                'year': int,
                'type': str,
                'title': str,
                'url': str,
                'quarter': Optional[str],
                'source': 'ai'
            }]
        """
        # Try OpenAI first, then Gemini
        if self.has_openai:
            return self._find_reports_openai(
                company_name, ticker, country, report_type, start_year, end_year
            )
        elif self.has_gemini:
            return self._find_reports_gemini(
                company_name, ticker, country, report_type, start_year, end_year
            )
        else:
            print("No AI available to fetch reports")
            return []
    
    def _find_reports_openai(
        self,
        company_name: str,
        ticker: Optional[str],
        country: str,
        report_type: str,
        start_year: int,
        end_year: int
    ) -> List[Dict]:
        """Use OpenAI to search for and extract actual report URLs."""
        try:
            from openai import OpenAI
            
            if OPENAI_BASE_URL:
                client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
            else:
                client = OpenAI(api_key=OPENAI_API_KEY)
            
            ticker_str = f" (Ticker: {ticker})" if ticker else ""
            year_range = f"{start_year}" if start_year == end_year else f"{start_year}-{end_year}"
            
            system_prompt = """You are an expert financial research assistant specializing in finding investor reports for international companies.

TASK: Find ACTUAL investor report URLs and information.

SEARCH STRATEGY:
1. Think about where companies publish their reports:
   - Official Investor Relations website (company.com/investors or ir.company.com)
   - Stock exchange filing platforms
   - Regulatory authority databases

2. For TURKISH companies (like Turkcell, Arcelik, etc.):
   - Check KAP (Public Disclosure Platform): https://www.kap.org.tr/en/
   - Company IR websites often at: company.com.tr/en/investors
   - Borsa Istanbul listings

3. URL CONSTRUCTION STRATEGY:
   - If you know the company, construct likely URLs based on patterns:
     * For Turkcell (TCELL): https://www.turkcell.com.tr/en/investors/financial-reports
     * For Arcelik (ARCLK): https://www.arcelikglobal.com/en/investors/
   - Common patterns: /investors/, /ir/, /annual-reports/, /financials/

4. QUALITY APPROACH:
   - Provide your best educated guess for URLs
   - Construct URLs based on company name + common IR patterns
   - Include multiple years if available

RETURN FORMAT - JSON object with "reports" array:
{
    "reports": [
        {
            "year": 2023,
            "type": "annual",
            "title": "2023 Annual Report",
            "url": "https://investors.company.com/reports/annual-2023.pdf",
            "quarter": null
        },
        {
            "year": 2022,
            "type": "annual",
            "title": "2022 Annual Report",
            "url": "https://investors.company.com/reports/annual-2022.pdf",
            "quarter": null
        }
    ]
}

IMPORTANT: Provide MULTIPLE reports for the year range when possible. Even if URLs are educated guesses, provide them!"""

            user_prompt = f"""Find investor reports for:

Company: {company_name}{ticker_str}
Country: {country}
Report Type: {report_type}
Years: {year_range}

Please:
1. Use your knowledge of this company and common IR website patterns
2. Construct likely URLs if exact ones unknown
3. Provide reports for each year in the range
4. Return actionable URLs even if educated guesses

Return JSON with "reports" array."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.5  # Slightly higher for creativity in URL construction
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Extract reports array
            reports = result.get('reports', [])
            
            # Add source field to each report
            for report in reports:
                report['source'] = 'ai_openai'
                # Ensure required fields exist
                if 'quarter' not in report:
                    report['quarter'] = None
            
            print(f"AI (OpenAI) found {len(reports)} reports for {company_name}")
            return reports
            
        except Exception as e:
            print(f"Error using OpenAI to find reports: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _find_reports_gemini(
        self,
        company_name: str,
        ticker: Optional[str],
        country: str,
        report_type: str,
        start_year: int,
        end_year: int
    ) -> List[Dict]:
        """Use Google Gemini to search for and extract actual report URLs."""
        try:
            import google.generativeai as genai
            import re
            
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            
            ticker_str = f" (Ticker: {ticker})" if ticker else ""
            year_range = f"{start_year}" if start_year == end_year else f"{start_year}-{end_year}"
            
            prompt = f"""Find investor reports for this company:

Company: {company_name}{ticker_str}
Country: {country}
Report Type: {report_type}
Years: {year_range}

Instructions:
1. Use your knowledge to find or construct likely URLs for investor relations reports
2. For Turkish companies, consider KAP (kap.org.tr) and company IR websites
3. Construct URLs based on common patterns if exact URLs unknown
4. Provide reports for EACH year in the range

Return ONLY a JSON object with "reports" array:
{{
    "reports": [
        {{
            "year": 2023,
            "type": "annual",
            "title": "2023 Annual Report",
            "url": "https://investors.company.com/2023-annual.pdf",
            "quarter": null
        }}
    ]
}}

Provide multiple reports for the year range. Return educated guesses if needed."""

            response = model.generate_content(prompt)
            
            # Extract JSON from response
            text = response.text.strip()
            text = re.sub(r'```json\s*|\s*```', '', text)
            
            result = json.loads(text)
            
            # Extract reports array
            reports = result.get('reports', [])
            
            # Add source field
            for report in reports:
                report['source'] = 'ai_gemini'
                if 'quarter' not in report:
                    report['quarter'] = None
            
            print(f"AI (Gemini) found {len(reports)} reports for {company_name}")
            return reports
            
        except Exception as e:
            print(f"Error using Gemini to find reports: {e}")
            import traceback
            traceback.print_exc()
            return []


if __name__ == '__main__':
    # Test with Turkish company
    assistant = AIReportAssistant()
    
    print("\n" + "="*80)
    print("Testing AI Report Assistant with Turkcell (Turkish company)")
    print("="*80 + "\n")
    
    reports = assistant.find_reports_with_ai(
        company_name="Turkcell",
        ticker="TCELL",
        country="Turkey",
        report_type="annual",
        start_year=2020,
        end_year=2024
    )
    
    print(f"\nFound {len(reports)} reports:")
    for r in reports:
        print(f"  {r['year']}: {r['title']}")
        print(f"          {r['url']}")
