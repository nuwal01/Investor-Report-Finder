import React from 'react'
import './AmbiguityModal.css'

/**
 * AmbiguityModal - Modal for resolving ambiguous company searches
 * 
 * Displays a list of matching companies when a search query returns multiple results.
 * Allows user to select the correct company or cancel.
 */
function AmbiguityModal({ isOpen, matches, query, onSelect, onCancel }) {
    if (!isOpen) return null

    return (
        <div className="ambiguity-modal-overlay">
            <div className="ambiguity-modal">
                <div className="ambiguity-modal-header">
                    <h3>Multiple Matches Found</h3>
                    <p>We found multiple companies matching "<strong>{query}</strong>". Please select the correct one:</p>
                </div>

                <div className="ambiguity-modal-body">
                    <div className="company-list">
                        {matches.map((company, index) => (
                            <div
                                key={`${company.ticker}-${index}`}
                                className="company-option"
                                onClick={() => onSelect(company)}
                            >
                                <div className="company-option-main">
                                    <span className="company-name">{company.company_name}</span>
                                    <div className="company-badges">
                                        <span className="ticker-badge">{company.ticker}</span>
                                        {company.exchange && (
                                            <span className={`exchange-badge exchange-${company.exchange.toLowerCase()}`}>
                                                {company.exchange}
                                            </span>
                                        )}
                                        {company.country && (
                                            <span className="country-badge">{company.country}</span>
                                        )}
                                    </div>
                                </div>
                                <div className="company-option-arrow">→</div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="ambiguity-modal-footer">
                    <button className="btn btn-secondary" onClick={onCancel}>
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    )
}

export default AmbiguityModal
