import React, { useState } from 'react';
import { API_URL } from '../config';
import './FinancialAnalysis.css';

export default function FinancialAnalysis({ ticker }) {
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleAnalyze = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/api/analyze-financials`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticker: ticker,
                    report_urls: [], // In a real app, we'd pass selected report URLs here
                    extract_from_pdfs: false
                })
            });

            if (!response.ok) throw new Error('Analysis failed');

            const data = await response.json();
            setAnalysis(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (!ticker) return null;

    return (
        <div className="financial-analysis-card">
            <div className="analysis-header">
                <h3>📊 Financial Analysis</h3>
                <button
                    className="analyze-button"
                    onClick={handleAnalyze}
                    disabled={loading}
                >
                    {loading ? 'Analyzing...' : 'Run Analysis'}
                </button>
            </div>

            {error && <div className="error-message">{error}</div>}

            {analysis && (
                <div className="analysis-results">
                    <div className="capabilities-section">
                        <h4>Available Capabilities</h4>
                        <div className="tags">
                            {Object.entries(analysis.capabilities).map(([key, value]) => (
                                <span key={key} className={`tag ${value ? 'active' : ''}`}>
                                    {key.replace(/_/g, ' ')}: {value.toString()}
                                </span>
                            ))}
                        </div>
                    </div>

                    <div className="message-box">
                        <p>{analysis.message}</p>
                    </div>
                </div>
            )}
        </div>
    );
}
