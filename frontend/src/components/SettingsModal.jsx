import { useState, useEffect } from 'react'
import './SettingsModal.css'

function SettingsModal({ isOpen, onClose }) {
    const [saving, setSaving] = useState(false)
    const [message, setMessage] = useState(null)
    const [showOpenAIKey, setShowOpenAIKey] = useState(false)
    const [showSerperKey, setShowSerperKey] = useState(false)
    const [settings, setSettings] = useState({
        openai_provider: 'openai',
        openai_api_key: '',
        openrouter_api_key: '',
        serper_api_key: '',
        tavily_api_key: ''
    })

    useEffect(() => {
        if (isOpen) {
            loadSettings()
        }
    }, [isOpen])

    const loadSettings = () => {
        try {
            const savedKeys = localStorage.getItem('apiKeys')
            if (savedKeys) {
                const data = JSON.parse(savedKeys)
                // Mask keys for display (show last 6 chars)
                const maskKey = (key) => {
                    if (!key || key.length < 10) return key || ''
                    return '••••••••••••••••' + key.slice(-6)
                }
                setSettings({
                    openai_provider: data.openai_provider || 'openai',
                    openai_api_key: maskKey(data.openai_api_key),
                    openrouter_api_key: maskKey(data.openrouter_api_key),
                    serper_api_key: maskKey(data.serper_api_key),
                    tavily_api_key: maskKey(data.tavily_api_key)
                })
            }
        } catch (error) {
            console.error('Error loading settings:', error)
        }
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setSaving(true)
        setMessage(null)

        try {
            // Get existing settings to merge with updates
            const existingKeys = JSON.parse(localStorage.getItem('apiKeys') || '{}')

            const updateData = {
                openai_provider: settings.openai_provider,
                openai_api_key: existingKeys.openai_api_key || '',
                openrouter_api_key: existingKeys.openrouter_api_key || '',
                serper_api_key: existingKeys.serper_api_key || '',
                tavily_api_key: existingKeys.tavily_api_key || ''
            }

            // Only update keys that were actually changed (not masked)
            if (settings.openai_api_key && !settings.openai_api_key.startsWith('••')) {
                updateData.openai_api_key = settings.openai_api_key
            }
            if (settings.openrouter_api_key && !settings.openrouter_api_key.startsWith('••')) {
                updateData.openrouter_api_key = settings.openrouter_api_key
            }
            if (settings.serper_api_key && !settings.serper_api_key.startsWith('••')) {
                updateData.serper_api_key = settings.serper_api_key
            }
            if (settings.tavily_api_key && !settings.tavily_api_key.startsWith('••')) {
                updateData.tavily_api_key = settings.tavily_api_key
            }

            // Save to localStorage
            localStorage.setItem('apiKeys', JSON.stringify(updateData))

            setMessage({ type: 'success', text: 'API keys saved successfully!' })
            setTimeout(() => {
                onClose()
                loadSettings()
            }, 1500)
        } catch (error) {
            console.error('Error saving settings:', error)
            setMessage({ type: 'error', text: 'Failed to save settings: ' + error.message })
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

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>🔧 LLM Provider:</label>
                        <div style={{ display: 'flex', gap: '20px', marginTop: '8px' }}>
                            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                                <input
                                    type="radio"
                                    name="provider"
                                    value="openai"
                                    checked={settings.openai_provider === 'openai'}
                                    onChange={(e) => handleChange('openai_provider', e.target.value)}
                                    style={{ marginRight: '8px' }}
                                />
                                OpenAI
                            </label>
                            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                                <input
                                    type="radio"
                                    name="provider"
                                    value="openrouter"
                                    checked={settings.openai_provider === 'openrouter'}
                                    onChange={(e) => handleChange('openai_provider', e.target.value)}
                                    style={{ marginRight: '8px' }}
                                />
                                OpenRouter (ChatGPT compatible)
                            </label>
                        </div>
                        <span className="help-text">Choose your preferred LLM provider for query parsing</span>
                    </div>
                    <div className="form-group">
                        <label htmlFor="openai_api_key">
                            OpenAI API Key (optional)
                            <span className="help-text">Used for query parsing. Get yours at platform.openai.com</span>
                        </label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type={showOpenAIKey ? 'text' : 'password'}
                                id="openai_api_key"
                                value={settings.openai_api_key}
                                onChange={(e) => handleChange('openai_api_key', e.target.value)}
                                placeholder="sk-..."
                                style={{ paddingRight: '40px' }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowOpenAIKey(!showOpenAIKey)}
                                style={{
                                    position: 'absolute',
                                    right: '10px',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer',
                                    fontSize: '16px'
                                }}
                            >
                                {showOpenAIKey ? (
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                                        <line x1="1" y1="1" x2="23" y2="23" />
                                    </svg>
                                ) : (
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                                        <circle cx="12" cy="12" r="3" />
                                    </svg>
                                )}
                            </button>
                        </div>
                    </div>

                    <div className="form-group">
                        <label htmlFor="serper_api_key">
                            Serper API Key (required) *
                            <span className="help-text">Used for web search. Get 2,500 free searches at serper.dev</span>
                        </label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type={showSerperKey ? 'text' : 'password'}
                                id="serper_api_key"
                                value={settings.serper_api_key}
                                onChange={(e) => handleChange('serper_api_key', e.target.value)}
                                placeholder="Enter Serper API Key"
                                style={{ paddingRight: '40px' }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowSerperKey(!showSerperKey)}
                                style={{
                                    position: 'absolute',
                                    right: '10px',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer',
                                    fontSize: '16px'
                                }}
                            >
                                {showSerperKey ? (
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                                        <line x1="1" y1="1" x2="23" y2="23" />
                                    </svg>
                                ) : (
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                                        <circle cx="12" cy="12" r="3" />
                                    </svg>
                                )}
                            </button>
                        </div>
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
            </div>
        </div>
    )
}

export default SettingsModal
