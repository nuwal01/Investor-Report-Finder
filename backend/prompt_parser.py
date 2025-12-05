"""
LLM-Based Prompt Parser for Investor Report Finder

Parses natural language prompts to extract company ticker, report type, and year range.
Supports OpenAI, Google Gemini, and regex fallback.
"""

import os
import re
import json
from typing import Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', '')  # Custom base URL (e.g., for OpenRouter)


class PromptParser:
    """Parses natural language prompts to extract report search parameters."""
    
    def __init__(self, company_mapping_file: str = 'company_mapping.json'):
        """Initialize the prompt parser.
        
        Args:
            company_mapping_file: Path to JSON file with company name → ticker mappings
        """
        self.company_mapping = self._load_company_mapping(company_mapping_file)
        
    def _load_company_mapping(self, filepath: str) -> Dict[str, str]:
        """Load company name to ticker mapping from JSON file."""
        try:
            # If filepath is relative, make it absolute relative to project root
            if not os.path.isabs(filepath):
                # Go up from backend/ to project root
                current_dir = Path(__file__).parent
                project_root = current_dir.parent
                filepath = str(project_root / filepath)
                
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Company mapping file not found: {filepath}")
            return {}
    
    def parse_prompt(self, prompt: str) -> Dict:
        """Main entry point to parse a natural language prompt.
        
        Args:
            prompt: User's natural language query
            
        Returns:
            Dictionary with extracted parameters:
            {
                'company': str,
                'ticker': str,
                'report_type': str,
                'start_year': int,
                'end_year': int,
                'confidence': float
            }
        """
        print(f"\n{'='*60}")
        print(f"Parsing prompt: '{prompt}'")
        print(f"{'='*60}\n")
        
        # Try LLM-based extraction first
        result = None
        
        if OPENAI_API_KEY:
            print("Using OpenAI for parsing...")
            result = self._extract_with_openai(prompt)
        elif GOOGLE_API_KEY:
            print("Using Google Gemini for parsing...")
            result = self._extract_with_gemini(prompt)
        
        # Fallback to regex if LLM failed or unavailable
        if not result:
            print("Using regex fallback parser...")
            result = self._extract_with_regex(prompt)
        
        # Validate and enrich result
        result = self._validate_and_enrich(result)
        
        print(f"\nParsed result:")
        print(f"  Company: {result.get('company', 'N/A')}")
        print(f"  Ticker: {result.get('ticker', 'N/A')}")
        print(f"  Report Type: {result.get('report_type', 'N/A')}")
        print(f"  Year Range: {result.get('start_year', 'N/A')} - {result.get('end_year', 'N/A')}")
        print(f"  Confidence: {result.get('confidence', 0):.2f}\n")
        
        return result
    
    def _extract_with_openai(self, prompt: str) -> Optional[Dict]:
        """Extract information using OpenAI API with structured output."""
        try:
            from openai import OpenAI
            
            # Use custom base URL if provided (for OpenRouter, Azure, etc.)
            if OPENAI_BASE_URL:
                client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
            else:
                client = OpenAI(api_key=OPENAI_API_KEY)
            
            system_prompt = """You are an expert at extracting information from investor report queries.

CRITICAL INSTRUCTIONS:
1. DISTINGUISH CLEARLY between Annual (10-K) and Quarterly (10-Q) reports.
   - 10-K = Annual Report (covers 12 months)
   - 10-Q = Quarterly Report (covers 3 months)
   - Q4 is NOT a 10-Q. Q4 data is included in the 10-K Annual Report.

2. WARNING: DO NOT confuse 10-K and 10-Q.
   - If user asks for "Quarterly", "10-Q", "Q1", "Q2", or "Q3" -> report_type = "quarterly"
   - If user asks for "Annual", "10-K", "Yearly" -> report_type = "annual"

Extract the following information:
1. Company name (e.g., "Apple", "Microsoft")
2. Company ticker symbol if mentioned (e.g., "AAPL", "MSFT")
3. Report type: "annual" or "quarterly"
4. Year or year range (e.g., 2020, or 2020-2024)

If year range is not specified but a single year is mentioned, use that year for both start and end.
If no year is specified, use the current year.

Return your response as JSON with these exact keys:
{
    "company": "company name",
    "ticker": "ticker symbol or empty string",
    "report_type": "annual or quarterly",
    "start_year": integer,
    "end_year": integer
}"""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            result = json.loads(response.choices[0].message.content)
            result['confidence'] = 0.95
            return result
            
        except ImportError:
            print("OpenAI package not installed. Install with: pip install openai")
            return None
        except Exception as e:
            print(f"Error using OpenAI: {e}")
            return None
    
    def _extract_with_gemini(self, prompt: str) -> Optional[Dict]:
        """Extract information using Google Gemini API."""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            
            gemini_prompt = f"""Extract the following information from this investor report query:
Query: "{prompt}"

CRITICAL RULES:
1. 10-K is ANNUAL (12 months). 10-Q is QUARTERLY (3 months).
2. DO NOT confuse them.
3. Q4 is part of the Annual Report (10-K), NOT a separate 10-Q.

Extract:
1. Company name
2. Company ticker symbol (if mentioned)
3. Report type (annual or quarterly)
   - "Quarterly", "10-Q", "Q1", "Q2", "Q3" -> quarterly
   - "Annual", "10-K", "Yearly" -> annual
4. Start year
5. End year (if range not specified, same as start year)

Return ONLY a JSON object with these exact keys:
{{
    "company": "company name",
    "ticker": "ticker symbol or empty string",
    "report_type": "annual or quarterly",
    "start_year": integer,
    "end_year": integer
}}"""

            response = model.generate_content(gemini_prompt)
            
            # Extract JSON from response
            text = response.text.strip()
            # Remove markdown code blocks if present
            text = re.sub(r'```json\s*|\s*```', '', text)
            
            result = json.loads(text)
            result['confidence'] = 0.90
            return result
            
        except ImportError:
            print("Google Generative AI package not installed. Install with: pip install google-generativeai")
            return None
        except Exception as e:
            print(f"Error using Gemini: {e}")
            return None
    
    def _extract_with_regex(self, prompt: str) -> Dict:
        """Fallback regex-based extraction."""
        result = {
            'company': '',
            'ticker': '',
            'report_type': 'annual',  # default
            'start_year': datetime.now().year,
            'end_year': datetime.now().year,
            'confidence': 0.5
        }
        
        # Extract report type
        if re.search(r'\b(quarterly|quarter|10-q|q[1-4])\b', prompt, re.IGNORECASE):
            result['report_type'] = 'quarterly'
        elif re.search(r'\b(annual|10-k|yearly)\b', prompt, re.IGNORECASE):
            result['report_type'] = 'annual'
        
        # Extract years
        years = re.findall(r'\b(20[0-9]{2})\b', prompt)
        if years:
            years = [int(y) for y in years]
            result['start_year'] = min(years)
            result['end_year'] = max(years)
        
        # Extract ticker (uppercase letters, 1-5 chars)
        ticker_match = re.search(r'\b([A-Z]{1,5})\b', prompt)
        if ticker_match:
            potential_ticker = ticker_match.group(1)
            # Avoid common false positives
            if potential_ticker not in ['PDF', 'IR', 'CEO', 'CFO', 'USA', 'FROM', 'GET']:
                result['ticker'] = potential_ticker
        
        # Try to extract company name (words before "annual" or "quarterly")
        company_match = re.search(r'\b(?:for|of)\s+([A-Z][a-zA-Z\s&\.]+?)(?:\s+(?:annual|quarterly|report|from|for|10-[KQ]))', prompt)
        if company_match:
            result['company'] = company_match.group(1).strip()
        
        return result
    
    def _validate_and_enrich(self, result: Dict) -> Dict:
        """Validate and enrich the parsed result."""
        if not result:
            return {
                'company': '',
                'ticker': '',
                'report_type': 'annual',
                'start_year': datetime.now().year,
                'end_year': datetime.now().year,
                'confidence': 0.0,
                'error': 'Failed to parse prompt'
            }
        
        # If we have a company name but no ticker, try to map it
        if result.get('company') and not result.get('ticker'):
            ticker = self._map_company_to_ticker(result['company'])
            if ticker:
                result['ticker'] = ticker
                result['confidence'] = min(result.get('confidence', 0.5) + 0.1, 1.0)
        
        # If we have a ticker but no company name, try reverse mapping
        if result.get('ticker') and not result.get('company'):
            # Try to find company name from ticker
            for company, ticker in self.company_mapping.items():
                if ticker == result['ticker'].upper():
                    result['company'] = company
                    break
        
        # Ensure report type is valid
        if result.get('report_type') not in ['annual', 'quarterly']:
            result['report_type'] = 'annual'
        
        # Ensure years are integers
        try:
            result['start_year'] = int(result.get('start_year', datetime.now().year))
            result['end_year'] = int(result.get('end_year', result['start_year']))
        except (ValueError, TypeError):
            result['start_year'] = datetime.now().year
            result['end_year'] = datetime.now().year
        
        # Ensure start <= end
        if result['start_year'] > result['end_year']:
            result['start_year'], result['end_year'] = result['end_year'], result['start_year']
        
        return result
    
    def _map_company_to_ticker(self, company_name: str) -> Optional[str]:
        """Map company name to ticker symbol.
        
        Args:
            company_name: Company name to look up
            
        Returns:
            Ticker symbol or None if not found
        """
        # Try exact match first
        if company_name in self.company_mapping:
            return self.company_mapping[company_name]
        
        # Try case-insensitive match
        for name, ticker in self.company_mapping.items():
            if name.lower() == company_name.lower():
                return ticker
        
        # Try partial match (company name contains or is contained in mapped name)
        company_lower = company_name.lower()
        for name, ticker in self.company_mapping.items():
            name_lower = name.lower()
            if company_lower in name_lower or name_lower in company_lower:
                return ticker
        
        return None


def main():
    """Test the prompt parser with sample queries."""
    parser = PromptParser()
    
    test_prompts = [
        "Download the annual report for Apple from 2020",
        "Get AAPL annual report 2020",
        "Show me Microsoft's quarterly reports for 2023-2024",
        "Find Tesla 10-K 2022",
        "I need Google's annual reports from 2020 to 2024",
        "Get me the quarterly reports for Meta in 2023",
    ]
    
    print("\n" + "="*60)
    print("TESTING PROMPT PARSER")
    print("="*60)
    
    for prompt in test_prompts:
        result = parser.parse_prompt(prompt)
        print()


if __name__ == '__main__':
    main()
