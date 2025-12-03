# Investor-Report-Finder

A Python-based scraping agent that finds and extracts investor relations reports (annual/quarterly PDFs) from company IR pages based on ticker symbol, report type, and date range.

## Features

- 🔍 **Automatic IR Page Discovery**: Uses Tavily API to find company investor relations pages
- 📄 **PDF Extraction**: Parses IR pages using BeautifulSoup to find all PDF reports
- 🎯 **Smart Filtering**: Filters reports by type (annual/quarterly) and year range
- ✅ **Compliance**: Respects robots.txt and implements rate limiting
- 🔄 **Fallback System**: Tries common IR URL patterns if API search fails
- 🤖 **Natural Language**: NEW! Use LLM-powered parsing to search with plain English

## Natural Language Search 🆕

Use plain English to search for investor reports:

```bash
# Interactive mode
python main.py

# Command-line mode
python main.py "Download the annual report for Apple from 2020"
python main.py "Get Microsoft quarterly reports from 2023 to 2024"
python main.py "Find Tesla's 10-K for 2022"
python main.py "I need Google's annual reports from the last 3 years"
```

The LLM parser automatically extracts:
- ✅ Company name → ticker symbol (Apple → AAPL)
- ✅ Report type (annual/quarterly/10-K/10-Q)  
- ✅ Year or year range

**Supported LLM Providers:**
- OpenAI (GPT-3.5/GPT-4) - Most accurate
- Google Gemini - Free tier available
- Regex fallback - Works without API keys (limited accuracy)

## Web Application 🌐

Run the full-stack web app:

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## Installation

1. **Clone or download this project**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API key**:
   - Sign up at [Tavily.com](https://tavily.com) to get an API key
   - Copy `.env.example` to `.env`:
     ```bash
     copy .env.example .env
     ```
   - Edit `.env` and add your API key:
     ```
     TAVILY_API_KEY=your_actual_api_key_here
     ```

## Usage

### Command Line

Search for annual reports:
```bash
python scraper.py --ticker AAPL --type annual --start-year 2020 --end-year 2024
```

Search for quarterly reports:
```bash
python scraper.py --ticker MSFT --type quarterly --start-year 2023 --end-year 2024
```

### Python API

```python
from scraper import IRReportFinder

# Initialize the finder
finder = IRReportFinder()

# Search for reports
reports = finder.search_reports(
    ticker='AAPL',
    report_type='annual',
    start_year=2020,
    end_year=2024
)

# Display results
for report in reports:
    print(f"Year: {report['year']}")
    print(f"Title: {report['text']}")
    print(f"URL: {report['url']}")
    print()
```

## Output Format

Each report is returned as a dictionary with the following fields:

```python
{
    'url': 'https://example.com/reports/annual-2023.pdf',
    'text': 'Annual Report 2023',
    'title': 'Apple Inc. Annual Report',
    'year': 2023,
    'type': 'annual'
}
```

## How It Works

1. **IR Page Discovery**: 
   - Uses Tavily API to search for "{ticker} investor relations"
   - Falls back to common URL patterns (investor.{company}.com) if API fails

2. **PDF Extraction**:
   - Parses the IR page HTML using BeautifulSoup
   - Finds all `<a>` tags with PDF links (ending in `.pdf`)
   - Extracts URL, link text, and title attributes

3. **Filtering**:
   - Matches report type using keywords:
     - Annual: "annual report", "10-K", "annual"
     - Quarterly: "quarterly", "10-Q", "quarter", "Q1/Q2/Q3/Q4"
   - Extracts year from filename/link text using regex
   - Returns only reports within specified year range

4. **Compliance**:
   - Checks `robots.txt` before scraping
   - Implements 2-second delay between requests
   - Uses proper User-Agent headers

## Examples

### Apple Annual Reports (2020-2024)
```bash
python scraper.py --ticker AAPL --type annual --start-year 2020 --end-year 2024
```

### Microsoft Quarterly Reports (2023-2024)
```bash
python scraper.py --ticker MSFT --type quarterly --start-year 2023 --end-year 2024
```

### Google Annual Reports (2022-2023)
```bash
python scraper.py --ticker GOOGL --type annual --start-year 2022 --end-year 2023
```

## Limitations

- Requires Tavily API key for best results (fallback available)
- IR page structure varies by company; some may not be parseable
- Some companies may block scraping via robots.txt
- PDF metadata extraction depends on consistent naming conventions

## License

MIT License - Feel free to use and modify as needed.
