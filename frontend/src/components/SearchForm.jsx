import { useState } from 'react'
import AmbiguityModal from './AmbiguityModal'
import { API_URL } from '../config'
import '../tabs.css'

function SearchForm({ onSearch, onReset, loading }) {
    const [prompt, setPrompt] = useState('')
    const [tickerInput, setTickerInput] = useState('')
    const [selectedCompany, setSelectedCompany] = useState(null)

    // Ambiguity handling
    const [showAmbiguityModal, setShowAmbiguityModal] = useState(false)
    const [ambiguousMatches, setAmbiguousMatches] = useState([])
    const [pendingSearchData, setPendingSearchData] = useState(null)

    const checkAmbiguity = async (query) => {
        try {
            const response = await fetch(`${API_URL}/api/resolve-company`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, max_results: 10 })
            })

            if (response.ok) {
                const data = await response.json()
                if (data.is_ambiguous && data.matches.length > 1) {
                    return data.matches
                }
            }
        } catch (err) {
            console.error('Ambiguity check error:', err)
        }
        return null
    }

    const handleSubmit = async (e) => {
        e.preventDefault()

        // Validate that either prompt or ticker is provided
        if (!prompt.trim() && !tickerInput.trim()) {
            alert('Please enter a search query or ticker symbol')
            return
        }

        let searchData = {}

        // If ticker provided, use it directly
        if (tickerInput.trim()) {
            searchData.ticker = tickerInput.trim().toUpperCase()
        }

        // Always include prompt (for AI parsing)
        if (prompt.trim()) {
            searchData.prompt = prompt.trim()
        }

        // If only ticker, still need prompt for completeness
        if (!searchData.prompt && searchData.ticker) {
            searchData.prompt = `Find investor reports for ${searchData.ticker}`
        }

        console.log('Submitting search:', searchData)
        onSearch(searchData)
    }

    const handleAmbiguitySelect = (company) => {
        setShowAmbiguityModal(false)
        setSelectedCompany(company)
        setTickerInput(company.ticker)

        if (pendingSearchData) {
            const finalSearchData = {
                ...pendingSearchData,
                ticker: company.ticker
            }
            onSearch(finalSearchData)
            setPendingSearchData(null)
        }
    }

    const handleReset = () => {
        setPrompt('')
        setTickerInput('')
        setSelectedCompany(null)
        onReset()
    }

    return (
        <>
            <form className="search-form" onSubmit={handleSubmit}>
                <div className="form-row">
                    <div className="form-group prompt-group">
                        <label htmlFor="prompt-input">
                            <span className="label-icon">💬</span> What are you looking for?
                        </label>
                        <textarea
                            id="prompt-input"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder={'E.g., "Annual report of Tesla 2023"\n      "Quarterly reports for AAPL from 2022 to 2024"\n      "Earnings releases of Turkcell"\n      "10-K for Microsoft 2023"'}
                            disabled={loading}
                            rows={4}
                            className="prompt-textarea"
                        />
                        <small className="help-text">
                            <strong>💡 Tip:</strong> Be specific! Include company name/ticker, report type, and years.
                        </small>
                    </div>
                </div>

                <div className="form-row">
                    <div className="form-group ticker-override-group">
                        <label htmlFor="ticker-input">
                            <span className="label-icon">📌</span> Ticker (Optional Override)
                        </label>
                        <input
                            id="ticker-input"
                            type="text"
                            value={tickerInput}
                            onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
                            placeholder="e.g., AAPL, TCELL, PETR4.SA"
                            disabled={loading}
                            className="ticker-input-field"
                        />
                        <small className="help-text">
                            Use this to specify a ticker if your prompt doesn't include one, or to override the ticker in your prompt
                        </small>
                    </div>
                </div>

                <div className="form-actions">
                    <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={loading || (!prompt.trim() && !tickerInput.trim())}
                    >
                        {loading ? '⏳ Searching...' : '🔍 Search Reports'}
                    </button>
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={handleReset}
                        disabled={loading}
                    >
                        🔄 Reset
                    </button>
                </div>

                <div className="search-info-box">
                    <div className="info-title">✨ Examples of what you can search:</div>
                    <ul className="info-list">
                        <li>"Annual reports for Apple from 2020 to 2024"</li>
                        <li>"Quarterly earnings of Arçelik (ARCLK) for 2023"</li>
                        <li>"Give me the 10-K of Tesla for 2022"</li>
                        <li>"Investor presentations from Petrobras in 2023"</li>
                        <li>"Financial statements of Turkcell TCELL"</li>
                    </ul>
                </div>
            </form>

            <AmbiguityModal
                isOpen={showAmbiguityModal}
                matches={ambiguousMatches}
                query={prompt}
                onSelect={handleAmbiguitySelect}
                onCancel={() => setShowAmbiguityModal(false)}
            />
        </>
    )
}

export default SearchForm
