import { useState, useEffect } from 'react'
import { useLocation, Link } from 'react-router-dom'
import { UserButton } from '@clerk/clerk-react'
import './App.css'

import SettingsModal from './components/SettingsModal'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function FinderApp() {

    const location = useLocation()
    const [prompt, setPrompt] = useState('')
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [showSettingsModal, setShowSettingsModal] = useState(false)
    const [apiKeys, setApiKeys] = useState(null)

    // Load API keys from localStorage for now (no auth)
    useEffect(() => {
        const savedKeys = localStorage.getItem('apiKeys')
        if (savedKeys) {
            setApiKeys(JSON.parse(savedKeys))
        }
    }, [])

    // Handle initial query from landing page
    useEffect(() => {
        if (location.state?.initialQuery) {
            setPrompt(location.state.initialQuery)
        }
    }, [location.state])

    const handleSearch = async (e) => {
        e.preventDefault()

        if (!prompt.trim()) {
            setError('Please enter a search query')
            return
        }

        setLoading(true)
        setError(null)
        setResults(null)

        try {
            // Use API keys from localStorage
            const openaiApiKey = apiKeys?.openai_api_key || apiKeys?.openrouter_api_key || ''
            const serperApiKey = apiKeys?.serper_api_key || ''
            const openaiProvider = apiKeys?.openai_provider || 'openai'

            const requestBody = {
                prompt: prompt.trim(),
                openai_api_key: openaiApiKey || undefined,
                serper_api_key: serperApiKey || undefined,
                openai_provider: openaiProvider
            }

            const response = await fetch(`${API_URL}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            })

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Search failed')
            }

            const data = await response.json()
            setResults(data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const handleReset = () => {
        setPrompt('')
        setResults(null)
        setError(null)
    }

    const examplePrompts = [
        "Annual reports for Apple from 2020 to 2024",
        "Quarterly earnings for Tesla Q1-Q4 2023",
        "10-K filings for Microsoft 2021-2023",
        "Financial statements of Turkcell TCELL"
    ]

    return (
        <div className="app">
            {/* Navigation Header */}
            <header className="navbar">
                <div className="navbar-content">
                    <Link to="/" className="navbar-brand">
                        <span className="navbar-icon">🔍</span>
                        <span>Investor-Report-Finder</span>
                    </Link>
                    <div className="navbar-actions">

                        <button
                            className="nav-button"
                            onClick={() => setShowSettingsModal(true)}
                        >
                            ⚙️ Settings
                        </button>
                        <UserButton afterSignOutUrl="/" />
                    </div>
                </div>
            </header>

            {/* Settings Modal */}
            <SettingsModal
                isOpen={showSettingsModal}
                onClose={() => setShowSettingsModal(false)}
            />

            {/* Main Content */}
            <main className="main-content">
                <div className="content-container">
                    {/* Hero Title */}
                    <div className="hero-section">
                        <h1 className="hero-title">
                            Find investor reports using <span className="highlight">natural language</span>
                        </h1>
                    </div>

                    {/* Search Card */}
                    <div className="search-card">
                        <form onSubmit={handleSearch} className="search-form">
                            <div className="form-group">
                                <label htmlFor="prompt" className="form-label">What are you looking for?</label>
                                <textarea
                                    id="prompt"
                                    value={prompt}
                                    onChange={(e) => setPrompt(e.target.value)}
                                    placeholder="e.g., Annual reports for Apple from 2020 to 2024"
                                    rows="4"
                                    className="search-input"
                                    disabled={loading}
                                />
                                <p className="input-hint">Press Enter to search</p>
                            </div>

                            <button
                                type="submit"
                                className="search-button"
                                disabled={loading || !prompt.trim()}
                            >
                                <span className="button-icon">🔍</span>
                                {loading ? 'Searching...' : 'Search Reports'}
                            </button>

                            {/* Example Prompts */}
                            <div className="examples-section">
                                <h3 className="examples-title">💡 Examples of what you can ask:</h3>
                                <div className="examples-grid">
                                    {examplePrompts.map((example, index) => (
                                        <div
                                            key={index}
                                            onClick={() => !loading && setPrompt(example)}
                                            className="example-box"
                                        >
                                            "{example}"
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </form>
                    </div>

                    {/* Error Display */}
                    {error && (
                        <div className="error-card">
                            <strong>❌ Error:</strong> {error}
                        </div>
                    )}

                    {/* Loading State */}
                    {loading && (
                        <div className="loading-state">
                            <div className="spinner"></div>
                            <p>Searching for reports...</p>
                        </div>
                    )}

                    {/* Results Display */}
                    {results && !loading && (
                        <div className="results-card">
                            <div className="results-header">
                                <h2>📊 Results</h2>
                                <p className="results-message">Found {results.count} report{results.count !== 1 ? 's' : ''}</p>
                            </div>

                            {/* Official Reports Pages Links */}
                            {results.reports_pages && results.reports_pages.length > 0 && (
                                <div className="reports-pages-section" style={{
                                    backgroundColor: '#e8f5e9',
                                    border: '1px solid #4caf50',
                                    borderRadius: '8px',
                                    padding: '12px 16px',
                                    marginBottom: '16px',
                                }}>
                                    <div style={{ fontWeight: '600', color: '#2e7d32', marginBottom: '8px' }}>
                                        📁 Official Reports Pages:
                                    </div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                                        {results.reports_pages.map((page, idx) => (
                                            <a key={idx}
                                                href={page.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{
                                                    color: '#1565c0',
                                                    textDecoration: 'none',
                                                    padding: '4px 10px',
                                                    backgroundColor: '#fff',
                                                    borderRadius: '4px',
                                                    border: '1px solid #bbdefb',
                                                    fontSize: '0.9rem'
                                                }}>
                                                {page.doc_category} →
                                            </a>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Missing Years Warning */}
                            {results.missing_years && results.missing_years.length > 0 && (
                                <div className="missing-years-notice" style={{
                                    backgroundColor: '#fff3cd',
                                    border: '1px solid #ffc107',
                                    borderRadius: '8px',
                                    padding: '12px 16px',
                                    marginBottom: '16px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '10px'
                                }}>
                                    <span style={{ fontSize: '1.2rem' }}>⚠️</span>
                                    <span style={{ color: '#856404' }}>
                                        Missing: {results.missing_years.sort((a, b) => a - b).join(', ')}
                                        (no official PDF found for {results.missing_years.length === 1 ? 'this year' : 'these years'})
                                    </span>
                                </div>
                            )}

                            {results.reports && results.reports.length > 0 ? (
                                <div className="reports-list">
                                    {/* Check if all results are IR pages (no PDFs found) */}
                                    {results.reports.every(r => r.type === 'investor_relations_page') ? (
                                        <div className="ir-page-fallback">
                                            <div className="ir-fallback-message">
                                                <span className="ir-icon">ℹ️</span>
                                                <div className="ir-text">
                                                    <p className="ir-notice">
                                                        We couldn't locate downloadable PDF reports for this company.
                                                        However, you can visit their official Investor Relations page to find the latest reports:
                                                    </p>
                                                </div>
                                            </div>
                                            {results.reports.map((report, index) => (
                                                <div key={index} className="ir-page-item">
                                                    <div className="report-info">
                                                        <span className="report-type ir-badge">Official IR Page</span>
                                                        <span className="report-title">{report.title}</span>
                                                    </div>
                                                    <a
                                                        href={report.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="ir-page-button"
                                                    >
                                                        🌐 Visit IR Page
                                                    </a>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        /* Normal PDF reports display */
                                        results.reports.map((report, index) => (
                                            report.type === 'investor_relations_page' ? (
                                                <div key={index} className="ir-page-item">
                                                    <div className="report-info">
                                                        <span className="report-type ir-badge">Official IR Page</span>
                                                        <span className="report-title">{report.title}</span>
                                                    </div>
                                                    <a
                                                        href={report.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="ir-page-button"
                                                    >
                                                        🌐 Visit IR Page
                                                    </a>
                                                </div>
                                            ) : (
                                                <div key={index} className="report-item">
                                                    <div className="report-info">
                                                        <span className="report-year">{report.reporting_period_year || report.year}</span>
                                                        <span className="report-type">{report.type}</span>
                                                        <span className="report-title">{report.title}</span>
                                                    </div>
                                                    <div className="report-actions">
                                                        <a
                                                            href={report.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="pdf-button"
                                                        >
                                                            📄 Open PDF
                                                        </a>
                                                        {report.source_page && (
                                                            <a
                                                                href={report.source_page}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="source-link"
                                                            >
                                                                🌐 Source
                                                            </a>
                                                        )}
                                                    </div>
                                                </div>
                                            )
                                        ))
                                    )}
                                </div>
                            ) : (
                                <div className="no-results">
                                    <p>No reports found. Try refining your search.</p>
                                </div>
                            )}
                        </div>
                    )}


                </div>
            </main>
        </div>
    )
}

export default FinderApp
