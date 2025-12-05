import { useState } from 'react'
import CompanyAutocomplete from './CompanyAutocomplete'
import AmbiguityModal from './AmbiguityModal'
import { API_URL } from '../config'
import '../tabs.css'

function SearchForm({ onSearch, onReset, loading }) {
    const [searchInput, setSearchInput] = useState('')
    const [tickerInput, setTickerInput] = useState('')
    const [selectedCompany, setSelectedCompany] = useState(null)
    const [reportType, setReportType] = useState('annual')
    const [startYear, setStartYear] = useState(2020)
    const [endYear, setEndYear] = useState(2024)

    // Ambiguity handling
    const [showAmbiguityModal, setShowAmbiguityModal] = useState(false)
    const [ambiguousMatches, setAmbiguousMatches] = useState([])
    const [pendingSearchData, setPendingSearchData] = useState(null)

    // Validation state
    const [validationMessage, setValidationMessage] = useState(null)
    const [validationStatus, setValidationStatus] = useState(null) // 'success', 'warning', 'error'

    const handleCompanySelect = (suggestion) => {
        setSelectedCompany(suggestion)
        setTickerInput(suggestion.ticker)  // Set ticker when company is selected
        setValidationMessage(null)
        setValidationStatus(null)
    }

    const verifyCompany = async (ticker, name) => {
        try {
            const response = await fetch(`${API_URL}/api/verify-company`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, company_name: name })
            })

            if (response.ok) {
                const data = await response.json()
                return data
            }
        } catch (err) {
            console.error('Verification error:', err)
        }
        return null
    }

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

        let searchData = {
            report_type: reportType,
            start_year: parseInt(startYear),
            end_year: parseInt(endYear)
        }

        // Prioritize ticker input if provided
        if (tickerInput.trim()) {
            searchData.ticker = tickerInput.trim().toUpperCase()
            onSearch(searchData)
            return
        }

        // Fall back to company name search
        if (!searchInput.trim()) {
            alert('Please enter either a company name or ticker symbol')
            return
        }

        // If company selected from autocomplete, use it directly
        if (selectedCompany) {
            searchData.ticker = selectedCompany.ticker
            onSearch(searchData)
            return
        }

        // Otherwise, process manual company name input
        const trimmedInput = searchInput.trim()

        // Check for ambiguity
        const matches = await checkAmbiguity(trimmedInput)
        if (matches) {
            setAmbiguousMatches(matches)
            setPendingSearchData(searchData)
            setShowAmbiguityModal(true)
            return
        }

        // If not ambiguous, proceed
        searchData.company_name = trimmedInput
        onSearch(searchData)
    }

    const handleAmbiguitySelect = (company) => {
        setShowAmbiguityModal(false)
        setSelectedCompany(company)
        setSearchInput(`${company.company_name} (${company.ticker})`)

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
        setSearchInput('')
        setTickerInput('')
        setSelectedCompany(null)
        setReportType('annual')
        setStartYear(2020)
        setEndYear(2024)
        setValidationMessage(null)
        setValidationStatus(null)
        onReset()
    }

    return (
        <>
            <form className="search-form" onSubmit={handleSubmit}>
                <div className="form-row">
                    <div className="form-group">
                        <label htmlFor="company-name-input">Company Name</label>
                        <input
                            id="company-name-input"
                            type="text"
                            value={searchInput}
                            onChange={(e) => setSearchInput(e.target.value)}
                            placeholder="e.g., Microsoft Corporation, Helios Towers plc"
                            disabled={loading}
                        />
                        <small>
                            Enter company name (e.g., Microsoft Corporation, NINtec Systems Ltd)
                        </small>
                    </div>

                    <div className="form-group">
                        <label htmlFor="ticker-input">Company Ticker</label>
                        <input
                            id="ticker-input"
                            type="text"
                            value={tickerInput}
                            onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
                            placeholder="e.g., AAPL, JSWSTEEL.NS, ULVR.L"
                            disabled={loading}
                            className="ticker-input"
                        />
                        <small>
                            Enter ticker symbol with exchange suffix for international stocks (e.g., JSWSTEEL.NS for India)
                        </small>
                    </div>
                </div>

                <div className="form-row">
                    <div className="form-group">
                        <label htmlFor="reportType">Report Type</label>
                        <select
                            id="reportType"
                            value={reportType}
                            onChange={(e) => setReportType(e.target.value)}
                            disabled={loading}
                        >
                            <option value="annual">Annual Report (10-K)</option>
                            <option value="quarterly">Quarterly Report (10-Q)</option>
                            <option value="earnings">Earnings Release</option>
                            <option value="presentation">Investor Presentation</option>
                            <option value="8-k">Current Report (8-K)</option>
                            <option value="financial_statements">Financial Statements</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label htmlFor="startYear">Start Year</label>
                        <input
                            id="startYear"
                            type="number"
                            min="2000"
                            max="2030"
                            value={startYear}
                            onChange={(e) => setStartYear(e.target.value)}
                            disabled={loading}
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="endYear">End Year</label>
                        <input
                            id="endYear"
                            type="number"
                            min="2000"
                            max="2030"
                            value={endYear}
                            onChange={(e) => setEndYear(e.target.value)}
                            disabled={loading}
                        />
                    </div>
                </div>

                <div className="form-actions">
                    <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={loading}
                    >
                        {loading ? 'Searching...' : '🔍 Search Reports'}
                    </button>
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={handleReset}
                        disabled={loading}
                    >
                        Reset
                    </button>
                </div>
            </form>

            <AmbiguityModal
                isOpen={showAmbiguityModal}
                matches={ambiguousMatches}
                query={searchInput}
                onSelect={handleAmbiguitySelect}
                onCancel={() => setShowAmbiguityModal(false)}
            />
        </>
    )
}

export default SearchForm
