import React, { useState } from 'react';
import { API_URL } from '../config';
import './TickerInfo.css';

export default function TickerInfo({ ticker }) {
    const [tickerInfo, setTickerInfo] = useState(null);
    const [loading, setLoading] = useState(false);

    const analyzeTicker = async () => {
        if (!ticker) return;

        setLoading(true);
        try {
            const response = await fetch(`${API_URL}/api/analyze-financials`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticker: ticker,
                    report_urls: [],
                    extract_from_pdfs: false
                })
            });

            const data = await response.json();
            setTickerInfo(data.ticker_info);
        } catch (error) {
            console.error('Error analyzing ticker:', error);
        } finally {
            setLoading(false);
        }
    };

    React.useEffect(() => {
        if (ticker && ticker.length > 0) {
            analyzeTicker();
        }
    }, [ticker]);

    if (!tickerInfo) return null;

    return (
        <div className="ticker-info-card">
            <h3>🌍 International Ticker Information</h3>
            <div className="info-grid">
                <div className="info-item">
                    <span className="label">Ticker:</span>
                    <span className="value">{tickerInfo.ticker}</span>
                </div>
                <div className="info-item">
                    <span className="label">Country:</span>
                    <span className="value">{tickerInfo.country}</span>
                </div>
                <div className="info-item">
                    <span className="label">Exchange:</span>
                    <span className="value">{tickerInfo.exchange_full}</span>
                </div>
                <div className="info-item">
                    <span className="label">Currency:</span>
                    <span className="value">{tickerInfo.currency}</span>
                </div>
                <div className="info-item">
                    <span className="label">Accounting:</span>
                    <span className="value">{tickerInfo.accounting_standard}</span>
                </div>
                <div className="info-item">
                    <span className="label">Regulatory Body:</span>
                    <span className="value">{tickerInfo.regulatory_body}</span>
                </div>
            </div>
        </div>
    );
}
