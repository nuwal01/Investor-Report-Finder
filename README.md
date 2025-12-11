# Investor-Report-Finder (OpenAI-Only Version)

A simplified, AI-powered tool to find investor relations reports using natural language queries and **OpenAI API only**.

## 🚀 Features

- **Natural Language Search**: Simply describe what you need (e.g., "Annual reports for Apple from 2020 to 2024")
- **Direct PDF URLs**: Get instant links to investor reports
- **OpenAI-Powered**: Uses OpenAI (or OpenRouter) to understand queries and find reports
- **Clean Interface**: Minimalist UI with prompt-based search
- **Global Coverage**: Supports companies from 40+ countries

## 🌍 Supported Countries

Users can search for companies from the following countries:

**Americas**: Argentina, Brazil, Canada, Cayman Islands, Chile, Colombia, Mexico, United States

**Europe**: Belgium, Cyprus, Lithuania, Luxembourg, Netherlands, Norway, Russia, Switzerland, Turkey, Ukraine, United Kingdom

**Middle East & Africa**: Bahrain, Egypt, Kuwait, Mauritius, Nigeria, Oman, Qatar, Saudi Arabia, South Africa, United Arab Emirates

**Asia-Pacific**: Azerbaijan, China, India, Indonesia, Kazakhstan, Singapore, Uzbekistan

**Multilaterals**: TDB (Trade and Development Bank), Afreximbank (African Export-Import Bank)

## 📋 Requirements

- Python 3.8+
- Node.js 16+
- **OpenAI API Key** (required) or OpenRouter API key

## 🛠️ Setup

### Backend

```bash
cd backend
pip install -r requirements.txt

# Configure your OpenAI API key
echo "OPENAI_API_KEY=your_openai_key_here" > ../.env

# Optional: Use OpenRouter instead
echo "OPENAI_PROVIDER=openrouter" >> ../.env
echo "OPENAI_BASE_URL=https://openrouter.ai/api/v1" >> ../.env

# Start the server
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## 🎯 Usage

1. Enter a natural language query in the prompt field:
   - "Annual reports for Apple from 2020 to 2024"
   - "Quarterly earnings for Tesla Q1-Q4 2023"
   - "10-K filings for Microsoft 2021-2023"

2. Click **Search Reports**

3. Get direct PDF links in clean list format:
   ```
   2024: Apple Inc. 2024 Annual Report [Open PDF]
   2023: Apple Inc. 2023 Annual Report [Open PDF]
   2022: Apple Inc. 2022 Annual Report [Open PDF]
   ```

## 🔑 API Key Configuration

### Option 1: Environment Variables (Recommended)
Add to `.env` file in the project root:
```bash
OPENAI_API_KEY=sk-...
```

### Option 2: Frontend Input
Click **⚙️ Settings** in the app and enter your API key. It will be sent with each request (not stored).

## 📦 Project Structure

```
.
├── backend/
│   ├── main.py                    # FastAPI server (OpenAI-only)
│   ├── openai_report_finder.py    # OpenAI-based report finder
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Simplified UI
│   │   └── App.css               # Modern dark theme
│   └── package.json
└── .env                           # API keys
```

## 🌐 API Endpoints

### `POST /search`
Search for reports using natural language.

**Request:**
```json
{
  "prompt": "Annual reports for Apple from 2020 to 2024",
  "openai_api_key": "sk-..." // optional if configured server-side
}
```

**Response:**
```json
{
  "success": true,
  "query": "Annual reports for Apple from 2020 to 2024",
  "reports": [
    {
      "year": 2024,
      "type": "annual",
      "title": "Apple Inc. 2024 Annual Report",
      "url": "https://example.com/report.pdf",
      "source": "openai"
    }
  ],
  "count": 1,
  "message": "Found 1 report(s) using OpenAI"
}
```

## 🎨 UI Preview

- **Dark Theme**: Modern gradient background with glassmorphism
- **Prompt Input**: Large textarea for natural language queries
- **Example Prompts**: Click to auto-fill common queries
- **Clean Results**: Year + Type + Title + "Open PDF" button

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `OPENAI_PROVIDER` | Provider: `openai` or `openrouter` | `openai` |
| `OPENAI_BASE_URL` | Custom API base URL | `https://api.openai.com/v1` |

## 🚨 Important Notes

1. **API Key Required**: The app will not work without an OpenAI or OpenRouter API key
2. **PDF URL Validation**: URLs are validated to ensure they point to actual PDF files
3. **No Storage**: Reports are not stored - only direct URLs are returned
4. **AI Limitations**: Report availability depends on OpenAI's web search capabilities

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Open an issue or submit a PR.

---

**Built with**: FastAPI, React (Vite), OpenAI API
