"""
Supabase Client for FastAPI Backend

Provides database operations for storing and retrieving user reports.
Uses Clerk user IDs (clerk_user_id) for user isolation.
"""

import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create the Supabase client singleton.
    Uses service key for backend operations.
    """
    global _supabase_client
    
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError(
                "Supabase credentials not configured. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env"
            )
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    return _supabase_client


# ============================================
# Report Storage Functions
# ============================================

def save_report(
    clerk_user_id: str,
    company_name: str,
    ticker: Optional[str],
    year: int,
    report_type: str,
    file_url: str,
    source_url: Optional[str] = None,
    title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a report to the database.
    
    Args:
        clerk_user_id: The Clerk user ID (from user["sub"])
        company_name: Company name
        ticker: Stock ticker symbol
        year: Report year
        report_type: Type of report (e.g., 'Annual Report', '10-K', 'Q1')
        file_url: URL to the PDF file
        source_url: Original source URL where report was found
        title: Report title
        
    Returns:
        The inserted record
    """
    client = get_supabase_client()
    
    data = {
        "clerk_user_id": clerk_user_id,
        "company_name": company_name,
        "ticker": ticker,
        "year": year,
        "report_type": report_type,
        "file_url": file_url,
        "source_url": source_url,
        "title": title,
        "status": "found"
    }
    
    result = client.table("reports").insert(data).execute()
    return result.data[0] if result.data else {}


def get_user_reports(
    clerk_user_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get all reports for a specific user.
    
    Args:
        clerk_user_id: The Clerk user ID (from user["sub"])
        limit: Maximum number of reports to return
        offset: Offset for pagination
        
    Returns:
        List of report records
    """
    client = get_supabase_client()
    
    result = client.table("reports") \
        .select("*") \
        .eq("clerk_user_id", clerk_user_id) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .offset(offset) \
        .execute()
    
    return result.data or []


def get_user_report_by_id(
    clerk_user_id: str,
    report_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a specific report by ID, ensuring it belongs to the user.
    
    Args:
        clerk_user_id: The Clerk user ID
        report_id: The report ID
        
    Returns:
        The report record or None if not found
    """
    client = get_supabase_client()
    
    result = client.table("reports") \
        .select("*") \
        .eq("id", report_id) \
        .eq("clerk_user_id", clerk_user_id) \
        .single() \
        .execute()
    
    return result.data


def delete_user_report(
    clerk_user_id: str,
    report_id: str
) -> bool:
    """
    Delete a report, ensuring it belongs to the user.
    
    Args:
        clerk_user_id: The Clerk user ID
        report_id: The report ID to delete
        
    Returns:
        True if deleted, False otherwise
    """
    client = get_supabase_client()
    
    result = client.table("reports") \
        .delete() \
        .eq("id", report_id) \
        .eq("clerk_user_id", clerk_user_id) \
        .execute()
    
    return len(result.data) > 0 if result.data else False


# ============================================
# Search History Functions (Optional)
# ============================================

def save_search_history(
    clerk_user_id: str,
    query: str,
    results_count: int
) -> Dict[str, Any]:
    """
    Save a search query to history.
    """
    client = get_supabase_client()
    
    data = {
        "clerk_user_id": clerk_user_id,
        "query": query,
        "results_count": results_count
    }
    
    result = client.table("search_history").insert(data).execute()
    return result.data[0] if result.data else {}


def get_user_search_history(
    clerk_user_id: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get recent search history for a user.
    """
    client = get_supabase_client()
    
    result = client.table("search_history") \
        .select("*") \
        .eq("clerk_user_id", clerk_user_id) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()
    
    return result.data or []


# ============================================
# User Settings Functions
# ============================================

def get_user_settings(clerk_user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user settings/preferences.
    """
    client = get_supabase_client()
    
    result = client.table("user_settings") \
        .select("*") \
        .eq("clerk_user_id", clerk_user_id) \
        .single() \
        .execute()
    
    return result.data


def upsert_user_settings(
    clerk_user_id: str,
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create or update user settings.
    """
    client = get_supabase_client()
    
    data = {
        "clerk_user_id": clerk_user_id,
        **settings
    }
    
    result = client.table("user_settings") \
        .upsert(data, on_conflict="clerk_user_id") \
        .execute()
    
    return result.data[0] if result.data else {}
