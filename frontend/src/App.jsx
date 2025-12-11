import { useState } from 'react'
import './App.css'
import { useTheme } from './context/ThemeContext'
import SettingsModal from './components/SettingsModal'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
    const { theme, toggleTheme } = useTheme()
    const [prompt, setPrompt] = useState('')
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [showSettingsModal, setShowSettingsModal] = useState(false)

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
            // Get API keys from localStorage
            const openaiApiKey = localStorage.getItem('openai_api_key') || ''
            const serperApiKey = localStorage.getItem('serper_api_key') || ''

            const requestBody = {
                prompt: prompt.trim(),
                openai_api_key: openaiApiKey || undefined,
                serper_api_key: serperApiKey || undefined
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
            <div className="container">
                <header className="header">
                    <div className="header-content">
                        <div>
                            <h1>🔍 Investor-Report-Finder</h1>
                            <p>Find investor reports using natural language</p>
                        </div>
                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <button
                                onClick={toggleTheme}
                                className="settings-button"
                                title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
                            >
                                {theme === 'light' ? '🌙' : '☀️'}
                            </button>
                            <button
                                className="settings-button"
                                onClick={() => setShowSettingsModal(true)}
                                title="API Settings"
                            >
                                ⚙️ Settings
                            </button>
                        </div>
                    </div>
                </header>

                {/* Settings Modal */}
                <SettingsModal
                    isOpen={showSettingsModal}
                    onClose={() => setShowSettingsModal(false)}
                />

                {/* Search Form */}
                <form onSubmit={handleSearch} className="search-form">
                    <div className="prompt-section">
                        <label htmlFor="prompt">What are you looking for?</label>
                        <textarea
                            id="prompt"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="e.g., Annual reports for Apple from 2020 to 2024"
                            rows="3"
                            className="prompt-input"
                            disabled={loading}
                        />
                    </div>

                    <div className="button-group">
                        <button
                            type="submit"
                            className="search-button"
                            disabled={loading || !prompt.trim()}
                        >
                            {loading ? '🔍 Searching...' : '🔍 Search Reports'}
                        </button>
                        {(results || error) && (
                            <button
                                type="button"
                                onClick={handleReset}
                                className="reset-button"
                                disabled={loading}
                            >
                                🔄 Reset
                            </button>
                        )}
                    </div>

                    {/* Example Prompts */}
                    <div className="examples-section">
                        <h3>💡 Examples of what you can ask:</h3>
                        <ul className="example-list">
                            {examplePrompts.map((example, index) => (
                                <li
                                    key={index}
                                    onClick={() => !loading && setPrompt(example)}
                                    className="example-item"
                                >
                                    "{example}"
                                </li>
                            ))}
                        </ul>
                    </div>
                </form>

                {/* Error Display */}
                {error && (
                    <div className="error-message">
                        <strong>❌ Error:</strong> {error}
                    </div>
                )}

                {/* Loading State */}
                {loading && (
                    <div className="loading">
                        <div className="spinner"></div>
                        <p>Searching for reports...</p>
                    </div>
                )}

                {/* Results Display */}
                {results && !loading && (
                    <div className="results-section">
                        <div className="results-header">
                            <h2>📊 Results</h2>
                            <p className="results-message">{results.message}</p>
                        </div>

                        {results.reports && results.reports.length > 0 ? (
                            <div className="reports-list">
                                {results.reports.map((report, index) => (
                                    <div key={index} className="report-item">
                                        <div className="report-info">
                                            <span className="report-year">{report.year}</span>
                                            <span className="report-type">{report.type}</span>
                                            <span className="report-title">{report.title}</span>
                                        </div>
                                        <a
                                            href={report.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="open-pdf-button"
                                        >
                                            📄 Open PDF
                                        </a>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="no-results">
                                <p>No reports found. Try refining your search.</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}

export default App
