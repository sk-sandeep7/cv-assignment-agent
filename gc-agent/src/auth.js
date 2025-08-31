// Auth utility functions
import API_BASE_URL from './config.js';

// Check if user session has expired and redirect to login if needed
export const handleAuthError = (response) => {
  if (response.status === 401) {
    // Clear any local storage if used
    localStorage.clear();
    // Redirect to login page
    window.location.href = '/';
    return true;
  }
  return false;
};

// Enhanced fetch wrapper that handles auth errors
export const authFetch = async (url, options = {}) => {
  const response = await fetch(url, {
    ...options,
    credentials: 'include', // Always include credentials
  });

  // Handle 401 errors (session expired)
  if (handleAuthError(response)) {
    throw new Error('Session expired');
  }

  return response;
};

// Check auth status with session expiry handling
export const checkAuthStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/check_auth`, {
      credentials: 'include'
    });
    const data = await response.json();
    
    if (data.message && data.message.includes('expired')) {
      console.log('Session expired after 7 days');
      // Could show a notification here
      return { logged_in: false, expired: true, message: data.message };
    }
    
    return data;
  } catch (error) {
    console.log('Auth check failed:', error);
    return { logged_in: false };
  }
};
