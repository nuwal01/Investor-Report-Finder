import { useState } from 'react'
import SearchForm from './components/SearchForm'
import ResultsDisplay from './components/ResultsDisplay'
import SettingsModal from './components/SettingsModal'
import TickerInfo from './components/TickerInfo'
import FinancialAnalysis from './components/FinancialAnalysis'
import ReportGenerator from './components/ReportGenerator'
import './App.css'

const API_URL = 'http://localhost:8000'

function App() {
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [settingsOpen, setSettingsOpen] = useState(false)
    const [currentTicker, setCurrentTicker] = useState(null)

    const handleSearch = async (searchData) => {
        setLoading(true)
        setError(null)
        setResults(null)
        if (searchData.ticker) {
            setCurrentTicker(searchData.ticker)
        }

        try {
            const response = await fetch(`${API_URL}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(searchData),
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
        setResults(null)
        setError(null)
        setCurrentTicker(null)
    }

    return (
        <div className="app">
            <div className="container">
                <header className="header">
                    <div className="header-content">
                        <div>
                            <h1>🔍 Investor-Report-Finder</h1>
                            <p>Find annual and quarterly reports for public companies</p>
                        </div>
                        <button
                            className="settings-button"
                            onClick={() => setSettingsOpen(true)}
                            title="API Settings"
                        >
                            ⚙️ API Settings
                        </button>
                    </div>
                </header>

                <SearchForm
                    onSearch={handleSearch}
                    onReset={handleReset}
                    loading={loading}
                />

                {error && (
                    <div className="error-message">
                        <strong>❌ Error:</strong> {error}
                    </div>
                )}

                {loading && (
                    <div className="loading">
                        <div className="spinner"></div>
                        <p>Searching for reports...</p>
                    </div>
                )}

                {/* Display International Ticker Info if available */}
                {currentTicker && !loading && (
                    <>
                        <TickerInfo ticker={currentTicker} />
                        {/* Temporarily hidden - not fully functional yet */}
                        {/* <FinancialAnalysis ticker={currentTicker} /> */}
                        {/* {results && (
                            <ReportGenerator
                                ticker={currentTicker}
                                reports={results}
                            />
                        )} */}
                    </>
                )}

                {results && !loading && (
                    <ResultsDisplay results={results} />
                )}
            </div>

            <SettingsModal
                isOpen={settingsOpen}
                onClose={() => setSettingsOpen(false)}
            />
        </div>
    )
}

export default App
