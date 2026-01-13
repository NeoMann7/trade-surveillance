/**
 * Centralized API configuration
 * Reads from environment variables with fallback to localhost for development
 */
// Get backend URL from environment variable, fallback to localhost
const BACKEND_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

console.log('🚀 API Config loaded! Backend URL:', BACKEND_URL);
console.log('🚀 Environment variable REACT_APP_API_URL:', process.env.REACT_APP_API_URL);

export const API_CONFIG = {
  baseUrl: BACKEND_URL,
  apiBase: `${BACKEND_URL}/api/surveillance`,
  uploadBase: `${BACKEND_URL}/api/upload`,
} as const;

// Helper function to get the full API URL
export const getApiUrl = (endpoint: string): string => {
  return `${BACKEND_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
};

