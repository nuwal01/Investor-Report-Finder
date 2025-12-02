"""
Company Name to Ticker Resolution Service

Provides fuzzy matching and resolution of company names to stock ticker symbols.
"""

import json
from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Dict, Optional, Tuple


class CompanyResolver:
    """Resolves company names to ticker symbols with fuzzy matching."""
    
    def __init__(self, mapping_file: Optional[Path] = None):
        """
        Initialize the resolver with company mapping data.
        
        Args:
            mapping_file: Path to company_mapping.json file
        """
        if mapping_file is None:
            # Default to company_mapping.json in project root
            # Check for enhanced mapping first
            root_dir = Path(__file__).parent.parent
            enhanced_file = root_dir / "company_mapping_enhanced.json"
            
            if enhanced_file.exists():
                mapping_file = enhanced_file
            else:
                mapping_file = root_dir / "company_mapping.json"
        
        self.mapping_file = mapping_file
        self.company_mapping = self._load_mapping()
        self.reverse_mapping = self._build_reverse_mapping()
    
    def _load_mapping(self) -> Dict[str, any]:
        """
        Load company mapping from JSON file.
        Supports both old format (name -> ticker) and new enhanced format.
        """
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if it's the new enhanced format
            if isinstance(data, dict) and "companies" in data:
                # New format: convert to internal structure
                mapping = {}
                for company in data["companies"]:
                    ticker = company["ticker"]
                    # Store full company info
                    mapping[ticker] = {
                        "ticker": ticker,
                        "exchange": company.get("exchange", ""),
                        "exchange_code": company.get("exchange_code", ""),
                        "country": company.get("country", ""),
                        "primary_name": company.get("primary_name", ""),
                        "legal_name": company.get("legal_name", ""),
                        "aliases": company.get("aliases", [])
                    }
                return mapping
            else:
                # Old format: simple name -> ticker dict
                # Convert to enhanced format for consistency
                mapping = {}
                reverse_map = {}
                
                for name, ticker in data.items():
                    if ticker not in reverse_map:
                        reverse_map[ticker] = []
                    reverse_map[ticker].append(name)
                
                for ticker, names in reverse_map.items():
                    mapping[ticker] = {
                        "ticker": ticker,
                        "exchange": "NASDAQ" if ticker.isupper() and len(ticker) <= 5 else "",
                        "exchange_code": "US",
                        "country": "United States",
                        "primary_name": names[0],
                        "legal_name": names[0],
                        "aliases": names
                    }
                
                return mapping
                
        except FileNotFoundError:
            print(f"Warning: Company mapping file not found at {self.mapping_file}")
            # Try the enhanced file
            enhanced_file = self.mapping_file.parent / "company_mapping_enhanced.json"
            if enhanced_file.exists():
                print(f"Attempting to load enhanced mapping from {enhanced_file}")
                self.mapping_file = enhanced_file
                return self._load_mapping()
            return {}
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {self.mapping_file}")
            return {}
    
    def _build_reverse_mapping(self) -> Dict[str, Dict]:
        """Build reverse mapping from ticker to company info."""
        return self.company_mapping.copy()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison (lowercase, strip whitespace)."""
        return text.lower().strip()
    
    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity score between two strings (0.0 to 1.0)."""
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _is_ticker_format(self, text: str) -> bool:
        """
        Check if input looks like a ticker symbol.
        
        Tickers are typically:
        - 1-5 characters
        - All uppercase (or will be converted to uppercase)
        - Alphabetic with possible dots
        """
        text = text.strip().upper()
        if len(text) > 5:
            return False
        # Allow letters and dots (for some international tickers)
        return all(c.isalpha() or c == '.' for c in text)
    
    def resolve(self, query: str, max_results: int = 5, min_score: float = 0.6) -> List[Dict[str, any]]:
        """
        Resolve a company name or ticker to possible matches.
        
        Args:
            query: Company name or ticker symbol
            max_results: Maximum number of results to return
            min_score: Minimum similarity score (0.0-1.0) for fuzzy matches
        
        Returns:
            List of matches with ticker, company_name, exchange, country, and confidence score
        """
        if not query or not query.strip():
            return []
        
        query_norm = self._normalize_text(query)
        query_upper = query.strip().upper()
        matches = []
        
        # Check if query is a ticker symbol
        if self._is_ticker_format(query):
            # Check if it's a valid ticker
            if query_upper in self.reverse_mapping:
                company_info = self.reverse_mapping[query_upper]
                return [{
                    'ticker': query_upper,
                    'company_name': company_info['primary_name'],
                    'exchange': company_info.get('exchange', ''),
                    'country': company_info.get('country', ''),
                    'match_type': 'exact_ticker',
                    'confidence': 1.0
                }]
        
        # Search through company names and aliases
        for ticker, company_info in self.company_mapping.items():
            primary_name = company_info['primary_name']
            aliases = company_info.get('aliases', [])
            all_names = [primary_name] + aliases
            
            best_match_type = None
            best_score = 0.0
            
            for name in all_names:
                name_norm = self._normalize_text(name)
                
                # Exact match (case-insensitive)
                if query_norm == name_norm:
                    best_match_type = 'exact'
                    best_score = 1.0
                    break
                
                # Starts with match (higher priority)
                if name_norm.startswith(query_norm):
                    score = 0.9 + (len(query_norm) / len(name_norm)) * 0.1
                    if score > best_score:
                        best_match_type = 'prefix'
                        best_score = min(score, 0.99)
                
                # Contains match
                elif query_norm in name_norm:
                    score = 0.7 + (len(query_norm) / len(name_norm)) * 0.2
                    if score > best_score:
                        best_match_type = 'contains'
                        best_score = min(score, 0.89)
                
                # Fuzzy match
                else:
                    similarity = self._similarity_score(query_norm, name_norm)
                    if similarity >= min_score and similarity > best_score:
                        best_match_type = 'fuzzy'
                        best_score = similarity
            
            # Add match if we found one
            if best_match_type and best_score > 0:
                matches.append({
                    'ticker': ticker,
                    'company_name': primary_name,
                    'exchange': company_info.get('exchange', ''),
                    'country': company_info.get('country', ''),
                    'match_type': best_match_type,
                    'confidence': best_score
                })
        
        # Sort by confidence (descending) and return top results
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        return matches[:max_results]
    
    def get_company_name(self, ticker: str) -> Optional[str]:
        """Get the primary company name for a ticker symbol."""
        ticker = ticker.upper().strip()
        company_info = self.reverse_mapping.get(ticker)
        if company_info:
            return company_info['primary_name']
        return None
    
    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Get full company information for a ticker symbol."""
        ticker = ticker.upper().strip()
        return self.reverse_mapping.get(ticker)
    
    def get_all_companies(self) -> List[Dict[str, str]]:
        """Get all companies in the mapping."""
        companies = []
        for ticker, company_info in self.company_mapping.items():
            companies.append({
                'ticker': ticker,
                'company_name': company_info['primary_name'],
                'exchange': company_info.get('exchange', ''),
                'country': company_info.get('country', '')
            })
        
        return sorted(companies, key=lambda x: x['company_name'])
    
    def detect_ambiguity(self, query: str) -> bool:
        """
        Detect if a query is ambiguous (multiple distinct companies match).
        
        Returns True if query matches multiple companies with different tickers.
        """
        matches = self.resolve(query, max_results=10, min_score=0.7)
        
        # Consider ambiguous if we have multiple high-confidence matches
        high_confidence_matches = [m for m in matches if m['confidence'] >= 0.8]
        
        return len(high_confidence_matches) > 1
    
    def verify_match(self, ticker: str, company_name: str) -> Dict[str, any]:
        """
        Verify if a ticker and company name refer to the same company.
        
        Args:
            ticker: Ticker symbol
            company_name: Company name to verify
        
        Returns:
            Dict with: is_valid, ticker, resolved_name, message, confidence
        """
        ticker = ticker.upper().strip()
        
        # Get company info from ticker
        company_info = self.reverse_mapping.get(ticker)
        
        if not company_info:
            return {
                'is_valid': False,
                'ticker': ticker,
                'resolved_name': None,
                'exchange': None,
                'country': None,
                'message': f"Ticker '{ticker}' not found in database",
                'confidence': 0.0
            }
        
        # Normalize and check if name matches
        name_norm = self._normalize_text(company_name)
        primary_norm = self._normalize_text(company_info['primary_name'])
        
        # Check exact match
        if name_norm == primary_norm:
            return {
                'is_valid': True,
                'ticker': ticker,
                'resolved_name': company_info['primary_name'],
                'exchange': company_info.get('exchange', ''),
                'country': company_info.get('country', ''),
                'message': f"Exact match: {company_info['primary_name']} ({ticker})",
                'confidence': 1.0
            }
        
        # Check aliases
        for alias in company_info.get('aliases', []):
            if name_norm == self._normalize_text(alias):
                return {
                    'is_valid': True,
                    'ticker': ticker,
                    'resolved_name': company_info['primary_name'],
                    'exchange': company_info.get('exchange', ''),
                    'country': company_info.get('country', ''),
                    'message': f"Matched via alias: {company_info['primary_name']} ({ticker})",
                    'confidence': 0.95
                }
        
        # Partial match
        if name_norm in primary_norm or primary_norm in name_norm:
            return {
                'is_valid': True,
                'ticker': ticker,
                'resolved_name': company_info['primary_name'],
                'exchange': company_info.get('exchange', ''),
                'country': company_info.get('country', ''),
                'message': f"Partial match: {company_info['primary_name']} ({ticker})",
                'confidence': 0.75
            }
        
        # No match - ticker exists but name doesn't match
        return {
            'is_valid': False,
            'ticker': ticker,
            'resolved_name': company_info['primary_name'],
            'exchange': company_info.get('exchange', ''),
            'country': company_info.get('country', ''),
            'message': f"Mismatch: Ticker '{ticker}' is {company_info['primary_name']}, not '{company_name}'",
            'confidence': 0.0
        }


# Singleton instance
_resolver_instance = None

def get_resolver() -> CompanyResolver:
    """Get the singleton CompanyResolver instance."""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = CompanyResolver()
    return _resolver_instance
