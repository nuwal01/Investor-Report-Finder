---
description: How to search for investor reports using the application
---

# Investor Report Finder Workflow

This workflow describes how to use the Investor Report Finder to search for annual reports, quarterly reports, and financial statements.

// turbo-all

## Prerequisites

1. Ensure you have API keys configured:
   - **OpenAI API Key** (required) - For AI-powered search
   - **Serper API Key** (optional) - For enhanced Google search

2. Start the application:
   ```bash
   cd Investor-Report-Finder
   start_app.bat
   ```

## Workflow Steps

### 1. Access the Application
- Open browser to http://localhost:5173
- Sign in if authentication is enabled

### 2. Configure API Keys (First Time)
- Click the **Settings** (⚙️) icon in the top-right
- Enter your OpenAI API key
- Optionally enter Serper API key
- Click **Save**

### 3. Search for Reports
Enter a natural language query in the search box. Examples:
- `Annual reports for Apple from 2020 to 2024`
- `Quarterly reports for Tesla Q1-Q4 2023`
- `10-K filings for Microsoft 2021-2023`
- `Annual financial statements for Tata Motors 2022-2024`

### 4. Review Results
Results include:
- **PDF Links**: Direct links to download reports
- **Year/Quarter**: The reporting period
- **Document Type**: Annual, Quarterly, 10-K, etc.
- **Source Page**: Link to the company's IR page

### 5. Handle Missing Reports
If some reports are not found:
- Check the **Notes** section for explanations
- Visit the **IR Page** link provided
- Try a more specific query

## Query Syntax

| Query Type | Example |
|------------|---------|
| Annual reports | `Annual reports for [Company] [Year Range]` |
| Quarterly reports | `Quarterly reports for [Company] Q1-Q4 [Year]` |
| Specific quarters | `[Company] Q2 2023 quarterly report` |
| 10-K filings | `10-K for [Company] [Year]` |
| 20-F filings | `20-F for [Company] [Year]` |

## Supported Document Types

- Annual Reports
- Quarterly Reports (Q1, Q2, Q3, Q4)
- Form 10-K (US SEC filing)
- Form 20-F (Foreign company SEC filing)
- Annual Financial Statements
- Interim Reports

## Troubleshooting

### No Results Found
1. Verify company name spelling
2. Check if company is publicly traded
3. Try using ticker symbol instead of company name
4. Narrow the year range

### Wrong Company Returned
1. Use the full legal company name
2. Include country or exchange (e.g., "Apple Inc. US")
3. Use the ticker symbol (e.g., "AAPL")

### Backend Not Responding
```bash
# Check if backend is running
curl http://localhost:8000/

# Restart backend
cd backend
.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check |
| `/search` | POST | Search for reports |
| `/discover` | POST | Advanced document discovery |
| `/company/resolve` | POST | Resolve company name |
| `/settings` | GET/POST | Manage API keys |
