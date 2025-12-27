import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { SignedIn, SignedOut, UserButton } from '@clerk/clerk-react'
import './LandingPage.css'

function LandingPage() {
    const navigate = useNavigate()
    const [searchQuery, setSearchQuery] = useState('')

    const handleSearch = (e) => {
        e.preventDefault()
        if (searchQuery.trim()) {
            // Navigate to app with the query stored
            navigate('/app', { state: { initialQuery: searchQuery } })
        }
    }

    const handleGetStarted = () => {
        navigate('/app')
    }

    return (
        <div className="landing-page">
            {/* Navigation Header */}
            <header className="landing-navbar">
                <div className="landing-navbar-content">
                    <div className="landing-logo">
                        <span className="landing-logo-icon">🔍</span>
                        <span className="landing-logo-text">Investor-Report-Finder</span>
                    </div>

                    <div className="landing-nav-actions">
                        <SignedOut>
                            <button className="landing-get-started-btn" onClick={handleGetStarted}>
                                Get Started
                            </button>
                        </SignedOut>
                        <SignedIn>
                            <button className="landing-get-started-btn" onClick={handleGetStarted}>
                                Go to App
                            </button>
                            <UserButton afterSignOutUrl="/" />
                        </SignedIn>
                    </div>
                </div>
            </header>

            {/* Hero Section */}
            <section className="landing-hero">
                <div className="landing-hero-content">
                    <h1 className="landing-hero-title">
                        Unlock Financial Insights.
                        <span className="landing-hero-highlight"> Search Reports.</span>
                    </h1>
                    <p className="landing-hero-subtitle">
                        Find investor reports using natural language.
                    </p>

                    <div className="landing-hero-search">
                        <form onSubmit={handleSearch} className="landing-hero-search-form">
                            <input
                                type="text"
                                className="landing-hero-search-input"
                                placeholder="Annual reports for Apple from 2020 to 2024."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                            <button type="submit" className="landing-hero-search-btn">
                                🔍 Search Reports
                            </button>
                        </form>
                    </div>
                </div>
                <div className="landing-hero-bg"></div>
            </section>

            {/* Feature Highlights Section */}
            <section className="landing-features">
                <h2 className="landing-section-title">Feature Highlights</h2>
                <p className="landing-section-subtitle">Find investor reports using natural language</p>

                <div className="landing-features-grid">
                    <div className="landing-feature-card">
                        <div className="landing-feature-icon">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#00BFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="11" cy="11" r="8" />
                                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                            </svg>
                        </div>
                        <h3 className="landing-feature-title">Natural Language Query</h3>
                        <p className="landing-feature-desc">
                            Search like you speak. Use natural language queries to find exactly what you need quickly and accurately.
                        </p>
                    </div>

                    <div className="landing-feature-card">
                        <div className="landing-feature-icon">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#00BFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="3" width="18" height="4" rx="1" fill="#00BFFF" />
                                <rect x="3" y="10" width="18" height="4" rx="1" fill="#00BFFF" />
                                <rect x="3" y="17" width="18" height="4" rx="1" fill="#00BFFF" />
                            </svg>
                        </div>
                        <h3 className="landing-feature-title">Global Report Database</h3>
                        <p className="landing-feature-desc">
                            Global report database consisting of thousands of filings, transcripts, and financial documents.
                        </p>
                    </div>

                    <div className="landing-feature-card">
                        <div className="landing-feature-icon">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#00BFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M12 3v12" />
                                <path d="M17 10l-5 5-5-5" />
                                <path d="M5 19h14" />
                            </svg>
                        </div>
                        <h3 className="landing-feature-title">Instant Access</h3>
                        <p className="landing-feature-desc">
                            Download transcripts instantly. Access data easier and faster than ever before.
                        </p>
                    </div>
                </div>
            </section>

            {/* Workflow Diagram Section */}
            <section className="landing-workflow">
                <h2 className="landing-section-title">Workflow Diagram</h2>
                <p className="landing-section-subtitle">Find investor reports for using the natural language</p>

                <div className="landing-workflow-steps">
                    <div className="landing-workflow-step">
                        <div className="landing-workflow-icon-box">
                            <div className="landing-workflow-icon">
                                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                    {/* Document with search */}
                                    <rect x="10" y="4" width="22" height="30" rx="2" fill="#E3F2FD" stroke="#00BFFF" strokeWidth="2" />
                                    <circle cx="28" cy="28" r="8" fill="white" stroke="#00BFFF" strokeWidth="2" />
                                    <line x1="34" y1="34" x2="40" y2="40" stroke="#00BFFF" strokeWidth="2.5" strokeLinecap="round" />
                                    <line x1="14" y1="12" x2="24" y2="12" stroke="#00BFFF" strokeWidth="2" strokeLinecap="round" />
                                    <line x1="14" y1="18" x2="20" y2="18" stroke="#00BFFF" strokeWidth="2" strokeLinecap="round" />
                                </svg>
                            </div>
                        </div>
                        <p className="landing-workflow-label">1. Type your request.</p>
                    </div>

                    <div className="landing-workflow-arrow">→</div>

                    <div className="landing-workflow-step">
                        <div className="landing-workflow-icon-box">
                            <div className="landing-workflow-icon">
                                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                    {/* AI Network Hub */}
                                    <rect x="18" y="18" width="12" height="12" rx="2" fill="#E3F2FD" stroke="#00BFFF" strokeWidth="2" />
                                    <text x="24" y="27" textAnchor="middle" fill="#00BFFF" fontSize="8" fontWeight="bold">AI</text>
                                    <circle cx="24" cy="8" r="4" fill="#00BFFF" />
                                    <circle cx="40" cy="24" r="4" fill="#00BFFF" />
                                    <circle cx="24" cy="40" r="4" fill="#00BFFF" />
                                    <circle cx="8" cy="24" r="4" fill="#00BFFF" />
                                    <circle cx="38" cy="10" r="3" fill="#00BFFF" />
                                    <circle cx="38" cy="38" r="3" fill="#00BFFF" />
                                    <circle cx="10" cy="38" r="3" fill="#00BFFF" />
                                    <circle cx="10" cy="10" r="3" fill="#00BFFF" />
                                    <line x1="24" y1="12" x2="24" y2="18" stroke="#00BFFF" strokeWidth="1.5" />
                                    <line x1="36" y1="24" x2="30" y2="24" stroke="#00BFFF" strokeWidth="1.5" />
                                    <line x1="24" y1="36" x2="24" y2="30" stroke="#00BFFF" strokeWidth="1.5" />
                                    <line x1="12" y1="24" x2="18" y2="24" stroke="#00BFFF" strokeWidth="1.5" />
                                </svg>
                            </div>
                        </div>
                        <p className="landing-workflow-label">2. Our AI searches.</p>
                    </div>

                    <div className="landing-workflow-arrow">→</div>

                    <div className="landing-workflow-step">
                        <div className="landing-workflow-icon-box">
                            <div className="landing-workflow-icon">
                                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                    {/* Document with download */}
                                    <rect x="10" y="4" width="22" height="30" rx="2" fill="#E3F2FD" stroke="#00BFFF" strokeWidth="2" />
                                    <circle cx="30" cy="30" r="10" fill="white" stroke="#00BFFF" strokeWidth="2" />
                                    <path d="M30 24v10" stroke="#00BFFF" strokeWidth="2" strokeLinecap="round" />
                                    <path d="M26 30l4 4 4-4" stroke="#00BFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                    <line x1="14" y1="12" x2="24" y2="12" stroke="#00BFFF" strokeWidth="2" strokeLinecap="round" />
                                    <line x1="14" y1="18" x2="20" y2="18" stroke="#00BFFF" strokeWidth="2" strokeLinecap="round" />
                                </svg>
                            </div>
                        </div>
                        <p className="landing-workflow-label">3. Download report.</p>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="landing-footer">
                <p>© 2023 Investor-Report-Finder. All rights reserved.</p>
            </footer>
        </div>
    )
}

export default LandingPage
