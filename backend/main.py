"""
FastAPI Backend for Investor-Report-Finder

Provides REST API endpoints for searching investor reports.
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path for Render compatibility
# This ensures local imports work regardless of how the app is started
BACKEND_DIR = Path(__file__).parent.absolute()
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from typing import Optional, List, Dict
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import OpenAI + Serper hybrid report finder
from openai_report_finder import OpenAISerperReportFinder

# Import Clerk authentication
from auth import get_current_user, get_optional_user

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Investor-Report-Finder API",
    description="Search for investor relations reports using ticker symbols or natural language",
    version="2.0.0"
)

# Configure CORS - Allow all origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (Vercel, localhost, etc.)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Request/Response Models
class SearchRequest(BaseModel):
    """Request model for search endpoint."""
    # Natural language prompt (REQUIRED)
    prompt: str = Field(..., description="Natural language query (e.g., 'Annual reports for Apple from 2020 to 2024')")
    
    # Optional: User-provided API keys
    openai_api_key: Optional[str] = Field(None, description="User's OpenAI API key")
    serper_api_key: Optional[str] = Field(None, description="User's Serper API key")
    
    # Optional: LLM Provider settings
    openai_provider: Optional[str] = Field(None, description="LLM provider (openai or openrouter)")
    openai_base_url: Optional[str] = Field(None, description="Custom base URL for LLM provider")

class ReportResponse(BaseModel):
    """Response model for a single report."""
    year: int
    type: str
    title: str
    url: str
    quarter: Optional[str] = None
    source: Optional[str] = None

class ReportsPageResponse(BaseModel):
    """Response model for a reports page."""
    doc_category: str
    url: str

class SearchResponse(BaseModel):
    """Response model for search results."""
    success: bool
    query: str  # Original prompt
    company: Optional[str] = None
    official_website: Optional[str] = None
    official_investor_relations: Optional[str] = None
    reports_pages: List[ReportsPageResponse] = []
    reports: List[ReportResponse]
    count: int
    message: str
    notes: Optional[str] = None
    missing_years: List[int] = []
    requested_years: List[int] = []

class CompanyResolveRequest(BaseModel):
    """Request model for company resolution."""
    query: str = Field(..., description="Company name or ticker to resolve")
    max_results: int = Field(5, description="Maximum number of results", ge=1, le=20)

class CompanyMatch(BaseModel):
    """Single company match result."""
    ticker: str
    company_name: str
    exchange: str
    country: str
    match_type: str
    confidence: float

class CompanyResolveResponse(BaseModel):
    """Response model for company resolution."""
    success: bool
    query: str
    matches: List[CompanyMatch]
    count: int
    is_ambiguous: bool = False  # True if multiple high-confidence matches

class CompanyVerifyRequest(BaseModel):
    """Request model for company verification."""
    ticker: str = Field(..., description="Ticker symbol to verify")
    company_name: str = Field(..., description="Company name to cross-check")

class CompanyVerifyResponse(BaseModel):
    """Response model for company verification."""
    is_valid: bool
    ticker: str
    resolved_name: Optional[str]
    exchange: Optional[str]
    country: Optional[str]
    message: str
    confidence: float

class SettingsRequest(BaseModel):
    """Request model for updating settings."""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API Key")
    serper_api_key: Optional[str] = Field(None, description="Serper API Key")
    openai_provider: Optional[str] = Field(None, description="OpenAI Provider (openai or openrouter)")
    openai_base_url: Optional[str] = Field(None, description="Custom OpenAI Base URL")

class SettingsResponse(BaseModel):
    """Response model for settings."""
    openai_api_key: str = Field(description="OpenAI API Key (masked)")
    serper_api_key: str = Field(description="Serper API Key (masked)")
    openai_provider: str = Field(description="OpenAI Provider")
    openai_base_url: str = Field(description="OpenAI Base URL")


# ============================================
# Financial Document Discovery Models
# ============================================

class DiscoveryRequest(BaseModel):
    """Request model for comprehensive document discovery."""
    company: str = Field(..., description="Company name or ticker symbol")
    start_year: Optional[int] = Field(None, description="Start year for search (default: current year - 5)")
    end_year: Optional[int] = Field(None, description="End year for search (default: current year)")
    report_types: Optional[List[str]] = Field(
        None, 
        description="List of report types: annual, quarterly, 10-k, 10-q, 20-f, interim, earnings, presentation"
    )
    max_results: int = Field(50, description="Maximum number of results", ge=1, le=100)
    
    # Optional: User-provided API keys
    serper_api_key: Optional[str] = Field(None, description="User's Serper API key")
    tavily_api_key: Optional[str] = Field(None, description="User's Tavily API key")


class DiscoveredDocumentResponse(BaseModel):
    """Response model for a discovered document."""
    company_name: str
    document_title: str
    reporting_period: str
    document_type: str
    pdf_url: str
    source_page_url: str
    language: str
    confidence_score: float
    year: Optional[int] = None
    quarter: Optional[str] = None


class DiscoveryResponse(BaseModel):
    """Response model for document discovery results."""
    success: bool
    company: str
    documents: List[DiscoveredDocumentResponse]
    total_count: int
    message: str
    search_metadata: Optional[Dict] = None


# Initialize OpenAI report finder (will be created per-request if user provides API key)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Investor-Report-Finder API v2.0 is running"}


# Protected endpoint example - requires Clerk authentication
from fastapi import Depends

@app.get("/api/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Get current authenticated user info.
    Requires valid Clerk JWT token in Authorization header.
    """
    return {
        "user_id": user.get("sub"),
        "email": user.get("email"),
        "session_id": user.get("sid"),
        "authenticated": True
    }


# ============================================
# Financial Document Discovery Endpoint
# ============================================

class DiscoverQueryRequest(BaseModel):
    """Request model for natural language document discovery."""
    query: str = Field(..., description="Natural language query (e.g., 'Annual reports for Apple from 2020 to 2024')")
    serper_api_key: Optional[str] = Field(None, description="User's Serper API key")


class DocumentOutput(BaseModel):
    """Output format for discovered document (required schema)."""
    title: str
    doc_type: str
    period: str
    pdf_url: str
    source_page: str


class DiscoverQueryResponse(BaseModel):
    """Response in the required JSON schema."""
    company: str
    request: Dict
    documents: List[DocumentOutput]
    notes: str


@app.post("/discover/query", response_model=DiscoverQueryResponse)
async def discover_documents_from_query(request: DiscoverQueryRequest):
    """
    Discover financial documents from a natural language query.
    
    Example: "Annual reports for Global Ports Delo Group from 2020 to 2024"
    
    This endpoint:
    - Does NOT stop at the IR homepage
    - Navigates deeper to find actual PDF files
    - Returns direct PDF links only
    - Uses fallback strategies for missing documents
    
    Returns JSON in the required schema:
    {
        "company": "string",
        "request": {"doc_types": [...], "date_range": "string"},
        "documents": [...],
        "notes": "string"
    }
    """
    try:
        print(f"\n{'='*60}")
        print(f"Document Discovery Query: {request.query}")
        print(f"{'='*60}")
        
        serper_key = request.serper_api_key or os.getenv("SERPER_API_KEY")
        
        if not serper_key:
            raise HTTPException(
                status_code=400,
                detail="Serper API key is required. Get one free at https://serper.dev"
            )
        
        # Use the natural language discovery function
        from document_discovery_agent import discover_investor_documents
        
        result = discover_investor_documents(
            query=request.query,
            serper_api_key=serper_key
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Discovery error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/discover", response_model=DiscoveryResponse)
async def discover_financial_documents(request: DiscoveryRequest):
    """
    Comprehensive financial document discovery with DEEP CRAWLING.
    
    This endpoint:
    - Does NOT stop at the IR homepage
    - Navigates deeper to "Reports & Presentations", "Financial Results", etc.
    - Only returns direct PDF links
    - Implements fallback strategies (SEC, regulators)
    
    Returns detailed document information including confidence scores.
    """
    try:
        print(f"\n{'='*60}")
        print(f"Document Discovery Request: {request.company}")
        print(f"Years: {request.start_year or 'auto'} - {request.end_year or 'auto'}")
        print(f"{'='*60}")
        
        # Get API keys
        serper_key = request.serper_api_key or os.getenv("SERPER_API_KEY")
        tavily_key = request.tavily_api_key or os.getenv("TAVILY_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not serper_key and not tavily_key:
            raise HTTPException(
                status_code=400,
                detail="Either Serper or Tavily API key is required for document discovery."
            )
        
        # Import and initialize discovery agent
        from document_discovery_agent import FinancialDocumentDiscoveryAgent
        
        agent = FinancialDocumentDiscoveryAgent(
            serper_api_key=serper_key,
            tavily_api_key=tavily_key,
            openai_api_key=openai_key,
        )
        
        # Discover documents (returns DiscoveryResult now)
        result = agent.discover_documents(
            company=request.company,
            doc_types=request.report_types,
            start_year=request.start_year,
            end_year=request.end_year,
            max_results=request.max_results,
        )
        
        # Convert to response format with detailed info
        doc_responses = []
        for doc_dict in result.documents:
            doc_responses.append(DiscoveredDocumentResponse(
                company_name=request.company,
                document_title=doc_dict.get('title', ''),
                reporting_period=doc_dict.get('period', ''),
                document_type=doc_dict.get('doc_type', ''),
                pdf_url=doc_dict.get('pdf_url', ''),
                source_page_url=doc_dict.get('source_page', ''),
                language='english',  # Default
                confidence_score=0.8,  # Default for results
                year=None,
                quarter=None,
            ))
        
        return DiscoveryResponse(
            success=True,
            company=request.company,
            documents=doc_responses,
            total_count=len(doc_responses),
            message=result.notes,
            search_metadata={
                "start_year": request.start_year,
                "end_year": request.end_year,
                "report_types": request.report_types,
                "sources_used": ["serper" if serper_key else None, "tavily" if tavily_key else None]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Discovery error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
async def search_reports(request: SearchRequest):
    """
    Search for investor reports using OpenAI + Serper (hybrid approach).
    
    Replicates ChatGPT's web browsing capability:
    1. OpenAI parses the query
    2. Serper searches Google for PDF URLs
    3. Returns actual PDF links
    """
    try:
        print(f"\n{'='*60}")
        print(f"Received search request: {request.prompt}")
        print(f"{'='*60}")
        
        # Get API keys (user-provided or from environment)
        openai_key = request.openai_api_key or os.getenv("OPENAI_API_KEY")
        serper_key = request.serper_api_key or os.getenv("SERPER_API_KEY")
        
        if not serper_key:
            raise HTTPException(
                status_code=400,
                detail="Serper API key is required. Get one free at https://serper.dev (2,500 searches/month free). Add to .env or provide in request."
            )
        
        # Determine base URL based on provider or custom URL
        base_url = request.openai_base_url
        if not base_url and request.openai_provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        elif not base_url and request.openai_provider == "openai":
            base_url = "https://api.openai.com/v1"
            
        # Initialize hybrid finder (OpenAI + Serper)
        finder = OpenAISerperReportFinder(
            openai_key=openai_key,
            serper_key=serper_key,
            base_url=base_url
        )
        
        # Find reports using hybrid approach (now returns dict)
        result = finder.find_reports(request.prompt)
        reports = result.get('reports', [])
        missing_years = result.get('missing_years', [])
        requested_years = result.get('requested_years', [])
        reports_pages = result.get('reports_pages', [])
        notes = result.get('notes', '')
        
        # Convert to response format
        report_objs = [ReportResponse(**r) for r in reports]
        
        # Build message with missing years info
        if report_objs:
            message = f"Found {len(report_objs)} report(s) using OpenAI + Serper (web search)"
            if missing_years:
                message += f". Missing years: {', '.join(map(str, missing_years))}"
        else:
            message = "No PDFs found after full retrieval ladder. "
            if reports_pages:
                message += f"Found {len(reports_pages)} reports page(s) - check manually."
            else:
                message += "Try refining your search."
        
        return {
            "success": True,
            "query": request.prompt,
            "company": result.get('company'),
            "official_website": result.get('official_website'),
            "official_investor_relations": result.get('official_investor_relations'),
            "reports_pages": reports_pages,
            "reports": jsonable_encoder(report_objs),
            "count": len(report_objs),
            "message": message,
            "notes": notes,
            "missing_years": missing_years,
            "requested_years": requested_years
        }
        
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Search error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/resolve-company", response_model=CompanyResolveResponse)
async def resolve_company(request: CompanyResolveRequest):
    """
    Resolve a company name or ticker to possible matches.
    
    This endpoint is used for autocomplete functionality in the frontend.
    Returns a list of possible matches with confidence scores.
    """
    try:
        if not request.query or not request.query.strip():
            return {
                "success": True,
                "query": request.query,
                "matches": [],
                "count": 0,
                "is_ambiguous": False
            }
        
        matches = company_resolver.resolve(
            query=request.query,
            max_results=request.max_results,
            min_score=0.5  # Lower threshold for autocomplete
        )
        
        # Detect ambiguity
        is_ambiguous = company_resolver.detect_ambiguity(request.query)
        
        match_objs = [CompanyMatch(**match) for match in matches]
        
        return {
            "success": True,
            "query": request.query,
            "matches": jsonable_encoder(match_objs),
            "count": len(match_objs),
            "is_ambiguous": is_ambiguous
        }
    
    except Exception as e:
        print(f"Company resolution error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/verify-company", response_model=CompanyVerifyResponse)
async def verify_company(request: CompanyVerifyRequest):
    """
    Verify if a ticker and company name refer to the same company.
    
    This endpoint is used for cross-validation when both ticker and name are provided.
    Returns validation result with confidence score.
    """
    try:
        result = company_resolver.verify_match(
            ticker=request.ticker,
            company_name=request.company_name
        )
        
        return CompanyVerifyResponse(**result)
    
    except Exception as e:
        print(f"Company verification error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current API keys (masked)."""
    def mask_key(key: Optional[str]) -> str:
        if not key or len(key) < 8:
            return "Not configured"
        return f"****{key[-4:]}"
    
    # Get provider settings with defaults
    provider = os.getenv("OPENAI_PROVIDER", "openai")
    base_url = os.getenv("OPENAI_BASE_URL", "")
    
    # Auto-detect provider from base URL if not explicitly set
    if not base_url and provider == "openai":
        base_url = "https://api.openai.com/v1"
    elif not base_url and provider == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
    
    return {
        "openai_api_key": mask_key(os.getenv("OPENAI_API_KEY")),
        "serper_api_key": mask_key(os.getenv("SERPER_API_KEY")),
        "openai_provider": provider,
        "openai_base_url": base_url
    }

@app.post("/settings")
async def update_settings(settings: SettingsRequest):
    """Update API keys in .env file."""
    try:
        env_path = Path(__file__).parent.parent / ".env"
        
        # Read existing .env content
        env_content = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key.strip()] = value.strip()
        
        # Update with new values (only if provided)
        if settings.openai_api_key:
            env_content['OPENAI_API_KEY'] = settings.openai_api_key
        if settings.serper_api_key:
            env_content['SERPER_API_KEY'] = settings.serper_api_key
        
        # Handle OpenAI provider settings
        if settings.openai_provider:
            env_content['OPENAI_PROVIDER'] = settings.openai_provider
            # Auto-set base URL based on provider if not explicitly provided
            if not settings.openai_base_url:
                if settings.openai_provider == "openrouter":
                    env_content['OPENAI_BASE_URL'] = "https://openrouter.ai/api/v1"
                elif settings.openai_provider == "openai":
                    env_content['OPENAI_BASE_URL'] = "https://api.openai.com/v1"
        
        # Allow manual base URL override
        if settings.openai_base_url:
            env_content['OPENAI_BASE_URL'] = settings.openai_base_url
        
        # Write back to .env
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        # Reload environment variables
        load_dotenv(override=True)
        
        return {" success": True, "message": "Settings updated successfully. Please restart the server for changes to take effect."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


# NEW: Financial Analysis Endpoints
class AnalysisRequest(BaseModel):
    """Request model for financial analysis."""
    ticker: str
    report_urls: List[str]
    extract_from_pdfs: bool = False  # Whether to extract data from PDFs (requires download)


class ReportGenerationRequest(BaseModel):
    """Request model for report generation."""
    ticker: str
    company_name: str
    reports: List[Dict]
    metrics: Optional[Dict] = None
    start_year: int
    end_year: int


@app.post("/api/analyze-financials")
async def analyze_financials(request: AnalysisRequest):
    """
    Analyze financial data from reports.
    
    NOTE: PDF extraction is currently limited - requires downloading PDFs.
    This endpoint provides structure for future full implementation.
    """
    try:
        from ticker_parser import TickerParser
        from financial_analyzer import FinancialAnalyzer
        
        ticker_parser = TickerParser()
        analyzer = FinancialAnalyzer()
        
        # Parse ticker to get country info
        ticker_info = ticker_parser.parse_ticker(request.ticker)
        
        # For now, return structure without actual PDF extraction
        # Full implementation requires downloading PDFs and extracting tables
        response = {
            'ticker': request.ticker,
            'ticker_info': ticker_info,
            'message': 'Financial analysis infrastructure ready. PDF extraction requires additional setup.',
            'capabilities': {
                'ticker_parsing': True,
                'multi_country_support': True,
                'ratio_calculation': True,
                'pdf_extraction': 'partial',  # Requires pdfplumber installation
                'report_generation': True
            }
        }
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/generate-report")
async def generate_report(request: ReportGenerationRequest):
    """Generate comprehensive financial analysis report."""
    try:
        from report_generator import FinancialReportGenerator
        from accounting_standards import AccountingStandardMapper
        
        generator = FinancialReportGenerator()
        standards_mapper = AccountingStandardMapper()
        
        # Prepare data for report
        report_data = {
            'ticker': request.ticker,
            'company_name': request.company_name,
            'start_year': request.start_year,
            'end_year': request.end_year,
            'num_reports': len(request.reports),
            'reports': request.reports,
            'metrics': request.metrics or {},
            'accounting_standard': 'To be detected from PDFs'
        }
        
        # Generate report
        markdown_report = generator.generate_full_report(report_data)
        
        return {
            'report': markdown_report,
            'format': 'markdown',
            'generated_at': str(datetime.now())
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# ============================================
# User Reports API (Supabase + Clerk)
# ============================================

# Import Supabase client functions
from supabase_client import (
    save_report,
    get_user_reports,
    get_user_report_by_id,
    delete_user_report,
    save_search_history,
    get_user_search_history
)


class SaveReportRequest(BaseModel):
    """Request model for saving a report."""
    company_name: str
    ticker: Optional[str] = None
    year: int
    report_type: str
    file_url: str
    source_url: Optional[str] = None
    title: Optional[str] = None


class SavedReportResponse(BaseModel):
    """Response model for a saved report."""
    id: str
    clerk_user_id: str
    company_name: str
    ticker: Optional[str]
    year: int
    report_type: str
    file_url: str
    source_url: Optional[str]
    title: Optional[str]
    status: str
    created_at: str


@app.post("/api/reports")
async def save_user_report(
    request: SaveReportRequest,
    user: dict = Depends(get_current_user)
):
    """
    Save a report to the user's collection.
    Requires Clerk authentication.
    """
    try:
        clerk_user_id = user.get("sub")
        if not clerk_user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        result = save_report(
            clerk_user_id=clerk_user_id,
            company_name=request.company_name,
            ticker=request.ticker,
            year=request.year,
            report_type=request.report_type,
            file_url=request.file_url,
            source_url=request.source_url,
            title=request.title
        )
        
        return {"success": True, "report": result}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save report: {str(e)}")


@app.get("/api/reports")
async def get_my_reports(
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user)
):
    """
    Get all reports saved by the current user.
    Requires Clerk authentication.
    """
    try:
        clerk_user_id = user.get("sub")
        if not clerk_user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        reports = get_user_reports(
            clerk_user_id=clerk_user_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "reports": reports,
            "count": len(reports)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reports: {str(e)}")


@app.get("/api/reports/{report_id}")
async def get_my_report(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get a specific report by ID.
    Requires Clerk authentication and ownership.
    """
    try:
        clerk_user_id = user.get("sub")
        if not clerk_user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        report = get_user_report_by_id(
            clerk_user_id=clerk_user_id,
            report_id=report_id
        )
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return {"success": True, "report": report}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get report: {str(e)}")


@app.delete("/api/reports/{report_id}")
async def delete_my_report(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Delete a report by ID.
    Requires Clerk authentication and ownership.
    """
    try:
        clerk_user_id = user.get("sub")
        if not clerk_user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        deleted = delete_user_report(
            clerk_user_id=clerk_user_id,
            report_id=report_id
        )
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Report not found or already deleted")
        
        return {"success": True, "message": "Report deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")


# ============================================
# Search History API
# ============================================

@app.get("/api/search-history")
async def get_my_search_history(
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """
    Get search history for the current user.
    Requires Clerk authentication.
    """
    try:
        clerk_user_id = user.get("sub")
        if not clerk_user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        history = get_user_search_history(
            clerk_user_id=clerk_user_id,
            limit=limit
        )
        
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get search history: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
