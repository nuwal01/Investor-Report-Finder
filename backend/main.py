"""
FastAPI Backend for Investor-Report-Finder

Provides REST API endpoints for searching investor reports.
"""

import sys
import os
from typing import Optional, List, Dict
from pathlib import Path
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Add parent directory to path to import scraper and parser
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from scraper import IRReportFinder
from prompt_parser import PromptParser
from company_resolver import get_resolver

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Investor-Report-Finder API",
    description="Search for investor relations reports using ticker symbols or natural language",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class SearchRequest(BaseModel):
    """Request model for search endpoint."""
    # Option 1: Manual parameters
    ticker: Optional[str] = Field(None, description="Company ticker symbol (e.g., AAPL)")
    company_name: Optional[str] = Field(None, description="Company name (e.g., Apple, Tesla Inc.)")
    report_type: Optional[str] = Field(None, description="Report type: annual, quarterly, earnings, presentation, 8-k, or financial_statements")
    start_year: Optional[int] = Field(None, description="Start year", ge=2000, le=2030)
    end_year: Optional[int] = Field(None, description="End year", ge=2000, le=2030)
    quarter: Optional[str] = Field(None, description="Specific quarter (Q1, Q2, Q3, Q4) - optional filter")
    
    # Option 2: Natural language prompt
    prompt: Optional[str] = Field(None, description="Natural language query (e.g., 'Find Apple 2023 annual report')")
    
    # Mode selection
    mode: str = Field("auto", description="Search mode: 'auto', 'manual', or 'prompt'")

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
    query: Dict
    reports: List[ReportResponse]
    count: int
    message: str
    resolved_company: Optional[Dict] = None  # Company name and ticker if resolved

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
    google_api_key: Optional[str] = Field(None, description="Google API Key")
    tavily_api_key: Optional[str] = Field(None, description="Tavily API Key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API Key")
    serper_api_key: Optional[str] = Field(None, description="Serper API Key")
    openai_provider: Optional[str] = Field(None, description="OpenAI Provider (openai or openrouter)")
    openai_base_url: Optional[str] = Field(None, description="Custom OpenAI Base URL")

class SettingsResponse(BaseModel):
    """Response model for settings."""
    google_api_key: str = Field(description="Google API Key (masked)")
    tavily_api_key: str = Field(description="Tavily API Key (masked)")
    openai_api_key: str = Field(description="OpenAI API Key (masked)")
    serper_api_key: str = Field(description="Serper API Key (masked)")
    openai_provider: str = Field(description="OpenAI Provider")
    openai_base_url: str = Field(description="OpenAI Base URL")


# Initialize services
scraper = IRReportFinder()
parser = PromptParser()
company_resolver = get_resolver()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Investor-Report-Finder API v2.0 is running"}

@app.post("/search", response_model=SearchResponse)
async def search_reports(request: SearchRequest):
    """
    Search for investor reports.
    
    Handles both structured requests (ticker, year, type) and natural language prompts.
    """
    try:
        search_params = {}
        resolved_company = None
        
        # Handle natural language prompt
        if request.prompt and (request.mode == "prompt" or request.mode == "auto" and not request.ticker and not request.company_name):
            print(f"Processing prompt: {request.prompt}")
            parsed = parser.parse_prompt(request.prompt)
            
            if not parsed:
                raise HTTPException(status_code=400, detail="Could not understand the prompt. Please try again or use manual search.")
                
            search_params = parsed
            # Override with any manual params if provided
            if request.ticker: search_params['ticker'] = request.ticker
            if request.company_name: 
                # Resolve company name to ticker
                matches = company_resolver.resolve(request.company_name, max_results=1)
                if matches:
                    search_params['ticker'] = matches[0]['ticker']
                    resolved_company = matches[0]
            if request.report_type: search_params['report_type'] = request.report_type
            
        # Handle manual parameters
        else:
            # Try to resolve company name if provided
            ticker = request.ticker
            if request.company_name and not ticker:
                matches = company_resolver.resolve(request.company_name, max_results=1)
                if matches:
                    ticker = matches[0]['ticker']
                    resolved_company = matches[0]
                else:
                    raise HTTPException(status_code=404, detail=f"Could not find company matching '{request.company_name}'. Please try a different name or use the ticker symbol.")
            
            if not ticker:
                raise HTTPException(status_code=400, detail="Either ticker symbol or company name is required for manual search.")
                
            search_params = {
                "ticker": ticker,
                "report_type": request.report_type or "annual",
                "start_year": request.start_year or 2020,
                "end_year": request.end_year or 2024
            }
            
            # If ticker was provided directly, try to get company name
            if request.ticker and not resolved_company:
                company_name = company_resolver.get_company_name(ticker)
                if company_name:
                    resolved_company = {
                        'ticker': ticker,
                        'company_name': company_name,
                        'match_type': 'direct_ticker',
                        'confidence': 1.0
                    }
            
        # Validate required fields
        if not search_params.get('ticker'):
             raise HTTPException(status_code=400, detail="Could not identify company ticker.")
             
        # Execute search
        print(f"Searching with params: {search_params}")
        reports = scraper.search_reports(
            ticker=search_params['ticker'],
            report_type=search_params.get('report_type', 'annual'),
            start_year=search_params.get('start_year'),
            end_year=search_params.get('end_year')
        )
        
        # Filter by quarter if specified
        if request.quarter:
            reports = [r for r in reports if r.get('quarter') == request.quarter]
        
        report_objs = [ReportResponse(**r) for r in reports]
        return {
            "success": True,
            "query": {**search_params, "mode": request.mode},
            "reports": jsonable_encoder(report_objs),
            "count": len(report_objs),
            "message": f"Found {len(report_objs)} report(s)" if report_objs else f"Could not find {search_params.get('report_type')} reports for {search_params.get('ticker')} ({search_params.get('start_year')}-{search_params.get('end_year')}). This might be due to robots.txt blocking or non-standard IR page structure.",
            "resolved_company": resolved_company
        }
        
    except Exception as e:
        print(f"Search error: {str(e)}")
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
        "google_api_key": mask_key(os.getenv("GOOGLE_API_KEY")),
        "tavily_api_key": mask_key(os.getenv("TAVILY_API_KEY")),
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
        if settings.google_api_key:
            env_content['GOOGLE_API_KEY'] = settings.google_api_key
        if settings.tavily_api_key:
            env_content['TAVILY_API_KEY'] = settings.tavily_api_key
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
