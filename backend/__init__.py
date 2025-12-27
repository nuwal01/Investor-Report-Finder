"""
Backend package for Investor-Report-Finder.

This package provides:
- FastAPI REST API endpoints
- Web scraping for investor reports
- Natural language prompt parsing
- Company name/ticker resolution
- Financial analysis tools
"""

import sys
from pathlib import Path

# Add the backend directory to Python path for Render compatibility
BACKEND_DIR = Path(__file__).parent.absolute()
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scraper import IRReportFinder
from prompt_parser import PromptParser
from company_resolver import get_resolver, CompanyResolver
from cache_manager import CacheManager

__all__ = [
    'IRReportFinder',
    'PromptParser', 
    'get_resolver',
    'CompanyResolver',
    'CacheManager'
]
