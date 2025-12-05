import { useState, useEffect } from 'react'
import { API_URL } from '../config'
import './SettingsModal.css'

function SettingsModal({ isOpen, onClose }) {
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [message, setMessage] = useState(null)
    const [settings, setSettings] = useState({
        google_api_key: '',
        tavily_api_key: '',
        openai_api_key: '',
        serper_api_key: ''
    })

    useEffect(() => {
        if (isOpen) {
            loadSettings()
        }
    }, [isOpen])

    const loadSettings = async () => {
        setLoading(true)
        setMessage(null)
        try {
            // Load from localStorage first (user's keys)
            const localKeys = {
                google_api_key: localStorage.getItem('google_api_key') || '',
                tavily_api_key: localStorage.getItem('tavily_api_key') || '',
                openai_api_key: localStorage.getItem('openai_api_key') || '',
                serper_api_key: localStorage.getItem('serper_api_key') || ''
            }

            // If we have local keys, use them
            if (localKeys.tavily_api_key || localKeys.serper_api_key) {
                setSettings(localKeys)
            } else {
                // Otherwise try to fetch from server (legacy support)
                try {
                    const response = await fetch(`${API_URL}/settings`)
                    if (response.ok) {
                        const data = await response.json()
                        setSettings({
                            google_api_key: data.google_api_key || '',
                            tavily_api_key: data.tavily_api_key || '',
                            openai_api_key: data.openai_api_key || '',
                            serper_api_key: data.serper_api_key || ''
                        })
                    }
                } catch (serverError) {
                    console.log('Server fetch failed (using local storage):', serverError)
                    setSettings(localKeys)
                }
            }
        } catch (error) {
            setMessage({ type: 'error', text: error.message })
        } finally {
            setLoading(false)
        }
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setSaving(true)
        setMessage(null)

        try {
            // Save to localStorage for client-side use
            if (settings.tavily_api_key && !settings.tavily_api_key.startsWith('****')) {
                localStorage.setItem('tavily_api_key', settings.tavily_api_key)
            }
            if (settings.serper_api_key && !settings.serper_api_key.startsWith('****')) {
                localStorage.setItem('serper_api_key', settings.serper_api_key)
            }
            if (settings.google_api_key && !settings.google_api_key.startsWith('****')) {
                localStorage.setItem('google_api_key', settings.google_api_key)
            }
            if (settings.openai_api_key && !settings.openai_api_key.startsWith('****')) {
                localStorage.setItem('openai_api_key', settings.openai_api_key)
            }

            // Also try to save to server (optional - may not be needed for user-managed keys)
            try {
                const response = await fetch(`${API_URL}/settings`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        google_api_key: settings.google_api_key.startsWith('****') ? null : settings.google_api_key,
                        tavily_api_key: settings.tavily_api_key.startsWith('****') ? null : settings.tavily_api_key,
                        openai_api_key: settings.openai_api_key.startsWith('****') ? null : settings.openai_api_key,
                        serper_api_key: settings.serper_api_key.startsWith('****') ? null : settings.serper_api_key
                    })
                })
                // Server save is optional - continue even if it fails
            } catch (serverError) {
                console.log('Server save failed (optional):', serverError)
            }

            setMessage({ type: 'success', text: 'API keys saved locally! They will be used for searches.' })
            setTimeout(() => {
                onClose()
            }, 2000)
        } catch (error) {
            setMessage({ type: 'error', text: error.message })
        } finally {
            setSaving(false)
        }
    }

    const handleChange = (field, value) => {
        setSettings(prev => ({ ...prev, [field]: value }))
    }

    if (!isOpen) return null

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-container" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>⚙️ API Settings</h2>
                    <button className="close-button" onClick={onClose}>×</button>
                </div>

                {loading ? (
                    <div className="loading-state">Loading settings...</div>
                ) : (
                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label htmlFor="google_api_key">
                                Google API Key
                                <span className="help-text">Used for Gemini LLM prompt parsing</span>
                            </label>
                            <input
                                type="text"
                                id="google_api_key"
                                value={settings.google_api_key}
                                onChange={(e) => handleChange('google_api_key', e.target.value)}
                                placeholder="Enter Google API Key"
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="tavily_api_key">
                                Tavily API Key
                                <span className="help-text">Used for direct report search</span>
                            </label>
                            <input
                                type="text"
                                id="tavily_api_key"
                                value={settings.tavily_api_key}
                                onChange={(e) => handleChange('tavily_api_key', e.target.value)}
                                placeholder="Enter Tavily API Key"
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="openai_api_key">
                                OpenAI API Key
                                <span className="help-text">Used for alternative LLM prompt parsing</span>
                            </label>
                            <input
                                type="text"
                                id="openai_api_key"
                                value={settings.openai_api_key}
                                onChange={(e) => handleChange('openai_api_key', e.target.value)}
                                placeholder="Enter OpenAI API Key"
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="serper_api_key">
                                Serper API Key
                                <span className="help-text">Used for alternative LLM prompt parsing</span>
                            </label>
                            <input
                                type="text"
                                id="serper_api_key"
                                value={settings.serper_api_key}
                                onChange={(e) => handleChange('serper_api_key', e.target.value)}
                                placeholder="Enter Serper API Key"
                            />
                        </div>

                        {message && (
                            <div className={`message ${message.type}`}>
                                {message.text}
                            </div>
                        )}

                        <div className="button-group">
                            <button type="button" className="cancel-button" onClick={onClose}>
                                Cancel
                            </button>
                            <button type="submit" className="save-button" disabled={saving}>
                                {saving ? 'Saving...' : 'Save Settings'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    )
}

export default SettingsModal
