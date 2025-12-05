// API Configuration
// Uses environment variable in production, falls back to localhost for development

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
