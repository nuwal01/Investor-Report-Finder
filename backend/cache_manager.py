"""
Cache Manager for Investor-Report-Finder

Handles SQLite-based caching of IR page URLs and report links.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

# DB path - go up from backend/ to project root
DB_PATH = Path(__file__).parent.parent / "cache.db"

class CacheManager:
    """Manages SQLite cache for IR pages and reports."""
    
    def __init__(self, db_path: Path = DB_PATH):
        """Initialize the cache manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for IR page URLs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ir_pages (
                ticker TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table for reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                year INTEGER NOT NULL,
                report_type TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, year, report_type, url)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_ir_page(self, ticker: str, max_age_days: int = 30) -> Optional[str]:
        """Get cached IR page URL for a ticker.
        
        Args:
            ticker: Company ticker symbol
            max_age_days: Maximum age of cached entry in days
            
        Returns:
            Cached URL or None if not found or expired
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT url, last_updated FROM ir_pages WHERE ticker = ?", 
            (ticker.upper(),)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        url, last_updated_str = row
        last_updated = datetime.fromisoformat(last_updated_str)
        
        # Check expiration
        if datetime.now() - last_updated > timedelta(days=max_age_days):
            return None
            
        return url
    
    def save_ir_page(self, ticker: str, url: str):
        """Save IR page URL to cache.
        
        Args:
            ticker: Company ticker symbol
            url: IR page URL
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO ir_pages (ticker, url, last_updated)
            VALUES (?, ?, ?)
        """, (ticker.upper(), url, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
    def get_reports(
        self, 
        ticker: str, 
        report_type: str, 
        start_year: int, 
        end_year: int,
        max_age_days: int = 30
    ) -> List[Dict]:
        """Get cached reports for a ticker within a year range.
        
        Args:
            ticker: Company ticker symbol
            report_type: 'annual' or 'quarterly'
            start_year: Start year
            end_year: End year
            max_age_days: Maximum age of cached entries
            
        Returns:
            List of report dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=max_age_days)).isoformat()
        
        cursor.execute("""
            SELECT year, report_type as type, url, title
            FROM reports 
            WHERE ticker = ? 
            AND report_type = ?
            AND year BETWEEN ? AND ?
            AND last_updated > ?
            ORDER BY year DESC
        """, (ticker.upper(), report_type, start_year, end_year, cutoff_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def save_reports(self, ticker: str, reports: List[Dict]):
        """Save reports to cache.
        
        Args:
            ticker: Company ticker symbol
            reports: List of report dictionaries
        """
        if not reports:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        for report in reports:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO reports 
                    (ticker, year, report_type, url, title, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    ticker.upper(),
                    report['year'],
                    report['type'],
                    report['url'],
                    report.get('text', ''),  # Use 'text' as title
                    timestamp
                ))
            except sqlite3.Error:
                continue
                
        conn.commit()
        conn.close()
