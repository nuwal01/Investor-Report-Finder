"""
Country Identifier Service

Uses AI (OpenAI GPT or Google Gemini) to identify the country of a company.
Determines whether Tavily/Serper should be used for search based on country.

ALLOWED COUNTRIES FOR TAVILY/SERPER: 30+ major markets
ALL OTHER COUNTRIES: AI-only responses
"""

import os
import sys
import json
from typing import Dict, Optional, List
from pathlib import Path
from dotenv import load_dotenv

# Add the backend directory to Python path for Render compatibility
BACKEND_DIR = Path(__file__).parent.absolute()
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load environment variables
load_dotenv()

# Get API keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', '')


class CountryIdentifier:
    """Identifies company country using AI reasoning."""
    
    # Countries allowed to use Tavily/Serper (EXPANDED LIST - 40+ countries)
    ALLOWED_COUNTRIES = {
        # Original 3
        'United States', 'USA', 'US',
        'India',
        'United Kingdom', 'UK', 'Britain', 'Great Britain',
        
        # New additions (alphabetically)
        'Argentina',
        'Azerbaijan',
        'Bahrain',
        'Belgium',
        'Brazil',
        'Canada',
        'Cayman Islands',
        'Chile',
        'China',
        'Colombia',
        'Cyprus',
        'Egypt',
        'Indonesia',
        'Kazakhstan',
        'Kuwait',
        'Lithuania',
        'Luxembourg',
        'Mauritius',
        'Mexico',
        'Netherlands',
        'Nigeria',
        'Norway',
        'Oman',
        'Qatar',
        'Russia',
        'Saudi Arabia',
        'Singapore',
        'South Africa',
        'Switzerland',
        'Turkey',
        'Ukraine',
        'United Arab Emirates', 'UAE',
        'Uzbekistan',
        
        # Regional multilaterals
        'TDB',  # Trade and Development Bank
        'Afreximbank'  # African Export-Import Bank
    }
    
    # Normalized country names for consistency
    COUNTRY_NORMALIZATION = {
        # USA variations
        'USA': 'United States',
        'US': 'United States',
        'United States of America': 'United States',
        
        # UK variations
        'UK': 'United Kingdom',
        'Britain': 'United Kingdom',
        'Great Britain': 'United Kingdom',
        
        # UAE variations
        'UAE': 'United Arab Emirates',
        'Emirates': 'United Arab Emirates',
        
        # Turkey variations
        'Republic of Turkey': 'Turkey',
        'Turkiye': 'Turkey',
        'Türkiye': 'Turkey',
        
        # Other common variations
        'Russian Federation': 'Russia',
        'PRC': 'China',
        "People's Republic of China": 'China',
        'Brasil': 'Brazil',
        'Republic of Korea': 'South Korea',
    }

    # Direct mappings for known companies to ensure accuracy
    DIRECT_MAPPINGS = {
        # Turkey
        'ARCLK': 'Turkey',
        'ARCELIK': 'Turkey',
        'TCELL': 'Turkey',
        'TURKCELL': 'Turkey',
        'THYAO': 'Turkey',
        'GARAN': 'Turkey',
        'AKBNK': 'Turkey',
        'KCHOL': 'Turkey',
        'SAHOL': 'Turkey',
        
        # Brazil
        'PETR4': 'Brazil',
        'PETROBRAS': 'Brazil',
        'VALE': 'Brazil',
        'ITUB': 'Brazil',
        'BBDC4': 'Brazil',
        
        # USA (Major Tech/Finance)
        'AAPL': 'United States',
        'MSFT': 'United States',
        'GOOGL': 'United States',
        'GOOG': 'United States',
        'AMZN': 'United States',
        'META': 'United States',
        'TSLA': 'United States',
        'NVDA': 'United States',
        'JPM': 'United States',
        'BAC': 'United States',
        'WMT': 'United States',
        'PG': 'United States',
        'V': 'United States',
        'MA': 'United States',
        
        # UK
        'ULVR': 'United Kingdom',
        'SHEL': 'United Kingdom',
        'BP': 'United Kingdom',
        'HSBC': 'United Kingdom',
        'AZN': 'United Kingdom',
        'DGE': 'United Kingdom',
        
        # India
        'RELIANCE': 'India',
        'TCS': 'India',
        'INFY': 'India',
        'HDFCBANK': 'India',
    }
    
    def __init__(self):
        """Initialize the country identifier."""
        self.has_openai = bool(OPENAI_API_KEY)
        self.has_gemini = bool(GOOGLE_API_KEY)
        
        # Import ticker parser for fallback
        from ticker_parser import TickerParser
        self.ticker_parser = TickerParser()

    def _generate_reason(self, country: str, allowed: bool) -> str:
        """Generate human-readable reason for routing decision."""
        normalized = self.normalize_country(country)
        
        if allowed:
            return f"Company from {normalized} - using Tavily/Serper search engines"
        else:
            return f"Company from {normalized} - using AI-only (Tavily/Serper available for 30+ major markets)"

    def is_allowed_country(self, country: str) -> bool:
        """Check if country is in the allowed list."""
        if not country:
            return False
            
        normalized = self.normalize_country(country)
        
        # Direct check
        if normalized in self.ALLOWED_COUNTRIES:
            return True
            
        # Case insensitive check
        return any(c.lower() == normalized.lower() for c in self.ALLOWED_COUNTRIES)

    def normalize_country(self, country: str) -> str:
        """Normalize country name."""
        if not country:
            return "Unknown"
            
        # Remove common prefixes/suffixes
        clean = country.strip()
        
        # Check explicit mappings
        if clean in self.COUNTRY_NORMALIZATION:
            return self.COUNTRY_NORMALIZATION[clean]
            
        # Case insensitive check
        clean_lower = clean.lower()
        for key, value in self.COUNTRY_NORMALIZATION.items():
            if key.lower() == clean_lower:
                return value
                
        return clean

    def identify_country(self, company_name: str = None, ticker: str = None) -> Dict:
        """
        Identify the country for a given company or ticker.
        Returns detailed info about routing decision.
        """
        if not company_name and not ticker:
            raise ValueError("Either company_name or ticker must be provided")
            
        # Strategy 0: Direct Mapping Check (Fast & Reliable)
        # Check ticker
        if ticker:
            clean_ticker = ticker.upper().split('.')[0]
            if clean_ticker in self.DIRECT_MAPPINGS:
                country = self.DIRECT_MAPPINGS[clean_ticker]
                allowed = self.is_allowed_country(country)
                print(f"DEBUG: Direct mapping: {clean_ticker} -> {country} (allowed: {allowed})")
                return {
                    'country': country,
                    'confidence': 1.0,
                    'method': 'direct_mapping',
                    'allowed_search_engines': ['tavily', 'serper'] if allowed else [],
                    'use_ai_only': not allowed,
                    'reason': self._generate_reason(country, allowed)
                }
        
        # Check company name
        if company_name:
            clean_name = company_name.upper().replace(' ', '')
            for key, country in self.DIRECT_MAPPINGS.items():
                if key in clean_name:
                    allowed = self.is_allowed_country(country)
                    print(f"DEBUG: Direct mapping via name: {clean_name} contains {key} -> {country}")
                    return {
                        'country': country,
                        'confidence': 1.0,
                        'method': 'direct_mapping',
                        'allowed_search_engines': ['tavily', 'serper'] if allowed else [],
                        'use_ai_only': not allowed,
                        'reason': self._generate_reason(country, allowed)
                    }
        
        # Strategy 1: Try ticker parser first if ticker has exchange suffix
        if ticker and '.' in ticker:
            ticker_country = self.ticker_parser.get_country_from_ticker(ticker)
            if ticker_country:
                # Normalize
                normalized = self.normalize_country(ticker_country)
                allowed = self.is_allowed_country(normalized)
                print(f"DEBUG: Ticker parser: {ticker} -> {normalized} (allowed: {allowed})")
                return {
                    'country': normalized,
                    'confidence': 0.9,
                    'method': 'ticker_suffix',
                    'allowed_search_engines': ['tavily', 'serper'] if allowed else [],
                    'use_ai_only': not allowed,
                    'reason': self._generate_reason(normalized, allowed)
                }

        # Strategy 2: Use AI to identify
        ai_country = self._identify_with_ai(company_name, ticker)
        print(f"DEBUG: AI Identified country: '{ai_country}' for {company_name or ticker}")
        
        if ai_country and ai_country != "Unknown":
            normalized = self.normalize_country(ai_country)
            allowed = self.is_allowed_country(normalized)
            return {
                'country': normalized,
                'confidence': 0.8,
                'method': 'ai_reasoning',
                'allowed_search_engines': ['tavily', 'serper'] if allowed else [],
                'use_ai_only': not allowed,
                'reason': self._generate_reason(normalized, allowed)
            }
            
        # Fallback
        print(f"DEBUG: Fallback to Unknown for {company_name or ticker}")
        return {
            'country': 'Unknown',
            'confidence': 0.0,
            'method': 'none',
            'allowed_search_engines': [],
            'use_ai_only': True,
            'reason': "Could not identify country - using AI-only for safety"
        }

    def _identify_with_ai(self, company_name: str, ticker: str) -> Optional[str]:
        """Use AI to identify country."""
        prompt = f"""Identify the headquarters country for this company:
Company: {company_name or 'Unknown'}
Ticker: {ticker or 'Unknown'}

Return ONLY the country name. Nothing else.
If you are not sure, return "Unknown".
Examples:
Apple -> United States
Turkcell -> Turkey
Samsung -> South Korea
"""

        # Try OpenAI first
        if self.has_openai:
            try:
                from openai import OpenAI
                
                if OPENAI_BASE_URL:
                    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
                else:
                    client = OpenAI(api_key=OPENAI_API_KEY)
                    
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a financial database assistant. Output only the country name."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Error using OpenAI for country identification: {e}")
                import traceback
                traceback.print_exc()

        # Try Gemini fallback
        if self.has_gemini:
            try:
                import google.generativeai as genai
                genai.configure(api_key=GOOGLE_API_KEY)
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                print(f"Error using Gemini for country identification: {e}")
                
        return "Unknown"
