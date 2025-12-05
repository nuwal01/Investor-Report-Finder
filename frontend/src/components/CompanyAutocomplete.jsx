import { useState, useEffect, useRef } from 'react'
import { API_URL } from '../config'
import './CompanyAutocomplete.css'

/**
 * CompanyAutocomplete - Autocomplete dropdown for company name/ticker search
 * 
 * Features:
 * - Debounced search as user types
 * - Keyboard navigation (arrow keys, enter, escape)
 * - Click outside to close
 * - Loading states
 */
function CompanyAutocomplete({ value, onChange, onSelect, disabled }) {
    const [suggestions, setSuggestions] = useState([])
    const [loading, setLoading] = useState(false)
    const [showDropdown, setShowDropdown] = useState(false)
    const [selectedIndex, setSelectedIndex] = useState(-1)
    const [error, setError] = useState(null)

    const dropdownRef = useRef(null)
    const inputRef = useRef(null)
    const debounceTimerRef = useRef(null)

    // Click outside to close dropdown
    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setShowDropdown(false)
            }
        }

        if (showDropdown) {
            document.addEventListener('mousedown', handleClickOutside)
            return () => document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [showDropdown])

    // Fetch suggestions when value changes
    useEffect(() => {
        // Clear previous timer
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current)
        }

        // Don't search if input is too short or empty
        if (!value || value.trim().length < 2) {
            setSuggestions([])
            setShowDropdown(false)
            return
        }

        // Debounce the API call
        debounceTimerRef.current = setTimeout(async () => {
            setLoading(true)
            setError(null)

            try {
                const response = await fetch(`${API_URL}/api/resolve-company`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        query: value,
                        max_results: 5
                    })
                })

                if (!response.ok) {
                    throw new Error('Failed to fetch suggestions')
                }

                const data = await response.json()
                setSuggestions(data.matches || [])
                setShowDropdown(data.matches && data.matches.length > 0)
                setSelectedIndex(-1)
            } catch (err) {
                console.error('Autocomplete error:', err)
                setError(err.message)
                setSuggestions([])
                setShowDropdown(false)
            } finally {
                setLoading(false)
            }
        }, 300) // 300ms debounce

        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current)
            }
        }
    }, [value])

    // Handle keyboard navigation
    const handleKeyDown = (e) => {
        if (!showDropdown || suggestions.length === 0) return

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault()
                setSelectedIndex(prev =>
                    prev < suggestions.length - 1 ? prev + 1 : prev
                )
                break
            case 'ArrowUp':
                e.preventDefault()
                setSelectedIndex(prev => prev > 0 ? prev - 1 : -1)
                break
            case 'Enter':
                e.preventDefault()
                if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
                    handleSelectSuggestion(suggestions[selectedIndex])
                }
                break
            case 'Escape':
                e.preventDefault()
                setShowDropdown(false)
                setSelectedIndex(-1)
                break
            default:
                break
        }
    }

    const handleSelectSuggestion = (suggestion) => {
        onSelect(suggestion)
        setShowDropdown(false)
        setSelectedIndex(-1)
        setSuggestions([])
    }

    const getConfidenceBadge = (confidence) => {
        if (confidence >= 0.95) return '✓'
        if (confidence >= 0.8) return '~'
        return '?'
    }

    const getMatchTypeLabel = (matchType) => {
        switch (matchType) {
            case 'exact':
            case 'exact_ticker':
                return 'Exact'
            case 'prefix':
                return 'Starts with'
            case 'contains':
                return 'Contains'
            case 'fuzzy':
                return 'Similar'
            default:
                return ''
        }
    }

    return (
        <div className="autocomplete-container" ref={dropdownRef}>
            <div className="autocomplete-input-wrapper">
                <input
                    ref={inputRef}
                    type="text"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                    placeholder="e.g., Apple, Tesla, AAPL, TSLA"
                    className="autocomplete-input"
                />
                {loading && (
                    <div className="autocomplete-loading">
                        <div className="spinner-small"></div>
                    </div>
                )}
            </div>

            {showDropdown && suggestions.length > 0 && (
                <div className="autocomplete-dropdown">
                    {suggestions.map((suggestion, index) => (
                        <div
                            key={`${suggestion.ticker}-${index}`}
                            className={`autocomplete-item ${index === selectedIndex ? 'selected' : ''}`}
                            onClick={() => handleSelectSuggestion(suggestion)}
                            onMouseEnter={() => setSelectedIndex(index)}
                        >
                            <div className="autocomplete-item-main">
                                <span className="company-name">{suggestion.company_name}</span>
                                <div className="ticker-exchange-group">
                                    <span className="ticker-badge">{suggestion.ticker}</span>
                                    {suggestion.exchange && (
                                        <span className={`exchange-badge exchange-${suggestion.exchange.toLowerCase()}`}>
                                            {suggestion.exchange}
                                        </span>
                                    )}
                                    {suggestion.country && suggestion.country !== 'United States' && (
                                        <span className="country-badge">{suggestion.country}</span>
                                    )}
                                </div>
                            </div>
                            <div className="autocomplete-item-meta">
                                <span className="match-type">{getMatchTypeLabel(suggestion.match_type)}</span>
                                <span className="confidence-badge">{getConfidenceBadge(suggestion.confidence)}</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {showDropdown && suggestions.length === 0 && !loading && value.trim().length >= 2 && (
                <div className="autocomplete-dropdown">
                    <div className="autocomplete-no-results">
                        No matching companies found
                    </div>
                </div>
            )}

            {error && (
                <div className="autocomplete-error">
                    {error}
                </div>
            )}
        </div>
    )
}

export default CompanyAutocomplete
