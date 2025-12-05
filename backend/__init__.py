"""
Backend package for Investor-Report-Finder.

This package provides:
- FastAPI REST API endpoints
- Web scraping for investor reports
- Natural language prompt parsing
- Company name/ticker resolution
- Financial analysis tools
"""

from backend.scraper import IRReportFinder
from backend.prompt_parser import PromptParser
from backend.company_resolver import get_resolver, CompanyResolver
from backend.cache_manager import CacheManager

__all__ = [
    'IRReportFinder',
    'PromptParser', 
    'get_resolver',
    'CompanyResolver',
    'CacheManager'
]
