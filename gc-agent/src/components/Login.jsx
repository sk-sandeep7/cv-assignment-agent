import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../Login.css';
import API_BASE_URL from '../config';

const Login = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Check if user is already authenticated
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/check_auth`, {
        credentials: 'include'
      });
      const data = await response.json();
      if (data.logged_in) {
        navigate('/home');
      }
    } catch (error) {
      console.log('Not authenticated');
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/google/url`, {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.auth_url) {
        // Redirect to Google OAuth
        window.location.href = data.auth_url;
      } else {
        throw new Error('Failed to get auth URL');
      }
    } catch (error) {
      console.error('Error initiating Google login:', error);
      alert('Failed to initiate Google login. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>Welcome to GC Agent</h1>
          <p>AI-powered Question Generation System</p>
        </div>
        
        <div className="login-content">
          <h2>Sign in to continue</h2>
          
          <button 
            onClick={handleGoogleLogin}
            className="google-login-btn"
            disabled={loading}
          >
            <div className="google-icon">
              <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
            </div>
            {loading ? 'Signing in...' : 'Sign in with Google'}
          </button>
          
          <div className="login-footer">
            <p>Secure authentication powered by Google</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
