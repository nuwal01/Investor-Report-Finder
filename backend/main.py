"""
FastAPI Backend for Investor-Report-Finder

Provides REST API endpoints for searching investor reports.
"""

import os
from typing import Optional, List, Dict
from pathlib import Path
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import OpenAI + Serper hybrid report finder
from openai_report_finder import OpenAISerperReportFinder

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

class ReportResponse(BaseModel):
    """Response model for a single report."""
    year: int
    type: str
    title: str
    url: str
    quarter: Optional[str] = None
    source: Optional[str] = None

class SearchResponse(BaseModel):
    """Response model for search results."""
    success: bool
    query: str  # Original prompt
    reports: List[ReportResponse]
    count: int
    message: str

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


# Initialize OpenAI report finder (will be created per-request if user provides API key)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Investor-Report-Finder API v2.0 is running"}

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
        
        # Initialize hybrid finder (OpenAI + Serper)
        finder = OpenAISerperReportFinder(
            openai_key=openai_key,
            serper_key=serper_key
        )
        
        # Find reports using hybrid approach
        reports = finder.find_reports(request.prompt)
        
        # Convert to response format
        report_objs = [ReportResponse(**r) for r in reports]
        
        # Build message
        if report_objs:
            message = f"Found {len(report_objs)} report(s) using OpenAI + Serper (web search)"
        else:
            message = "No reports found. Try refining your search or check if reports are available for the requested period."
        
        return {
            "success": True,
            "query": request.prompt,
            "reports": jsonable_encoder(report_objs),
            "count": len(report_objs),
            "message": message
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
        from backend.ticker_parser import TickerParser
        from backend.financial_analyzer import FinancialAnalyzer
        
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
        from backend.report_generator import FinancialReportGenerator
        from backend.accounting_standards import AccountingStandardMapper
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
