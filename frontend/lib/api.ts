const DEFAULT_API_BASE_URL = 'https://graphtal-tool-production-07b7.up.railway.app'

const configuredBaseUrl = process.env.NEXT_PUBLIC_API_URL?.trim()

export const API_BASE_URL = (configuredBaseUrl || DEFAULT_API_BASE_URL).replace(/\/$/, '')
