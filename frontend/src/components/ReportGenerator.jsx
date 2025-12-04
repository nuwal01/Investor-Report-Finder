import React, { useState } from 'react';
import './ReportGenerator.css';

export default function ReportGenerator({ ticker, companyName, reports }) {
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleGenerate = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('http://localhost:8000/api/generate-report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticker: ticker,
                    company_name: companyName || ticker,
                    reports: reports || [],
                    start_year: 2020, // Default range
                    end_year: 2024
                })
            });

            if (!response.ok) throw new Error('Report generation failed');

            const data = await response.json();
            setReport(data.report);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (!ticker) return null;

    return (
        <div className="report-generator-card">
            <div className="report-header">
                <h3>📝 Report Generator</h3>
                <button
                    className="generate-button"
                    onClick={handleGenerate}
                    disabled={loading}
                >
                    {loading ? 'Generating...' : 'Generate Report'}
                </button>
            </div>

            {error && <div className="error-message">{error}</div>}

            {report && (
                <div className="report-content">
                    <pre>{report}</pre>
                    <div className="report-actions">
                        <button
                            className="download-button"
                            onClick={() => {
                                const blob = new Blob([report], { type: 'text/markdown' });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = `${ticker}_Financial_Report.md`;
                                a.click();
                            }}
                        >
                            💾 Download Markdown
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
