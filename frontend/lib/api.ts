const LOCAL_API_BASE_URL = 'http://localhost:8000'
const PRODUCTION_API_BASE_URL = 'https://graphtal-tool-production-07b7.up.railway.app'

// Use environment variable if set, otherwise default to local for development
const configuredBaseUrl = process.env.NEXT_PUBLIC_API_URL?.trim()

// Determine which base URL to use
export const API_BASE_URL = (configuredBaseUrl || LOCAL_API_BASE_URL).replace(/\/$/, '')

// Export both URLs for reference if needed
export const LOCAL_API_URL = LOCAL_API_BASE_URL
export const PRODUCTION_API_URL = PRODUCTION_API_BASE_URL
