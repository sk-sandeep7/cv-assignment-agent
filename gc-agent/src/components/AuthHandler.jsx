import React, { useEffect } from 'react';
import API_BASE_URL from '../config';

const AuthHandler = () => {
  useEffect(() => {
    const handleAuthCallback = async () => {
      // Check if we have an auth_token in the URL
      const urlParams = new URLSearchParams(window.location.search);
      const authToken = urlParams.get('auth_token');
      
      if (authToken) {
        console.log('🔑 Auth token found in URL, creating session token...');
        
        try {
          // Create a long-term session token
          const response = await fetch(`${API_BASE_URL}/api/auth/create-session-token`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ auth_token: authToken })
          });
          
          if (response.ok) {
            const data = await response.json();
            const sessionToken = data.session_token;
            
            // Store session token in localStorage
            localStorage.setItem('session_token', sessionToken);
            console.log('✅ Session token stored in localStorage');
            
            // Clean up URL
            window.history.replaceState({}, document.title, window.location.pathname);
            
            // Redirect to home or refresh page
            window.location.href = '/';
            
          } else {
            console.error('❌ Failed to create session token');
            localStorage.removeItem('session_token');
          }
          
        } catch (error) {
          console.error('❌ Error creating session token:', error);
          localStorage.removeItem('session_token');
        }
      }
    };
    
    handleAuthCallback();
  }, []);
  
  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh',
      backgroundColor: '#FFF9F2'
    }}>
      <div style={{ 
        textAlign: 'center',
        padding: '2rem',
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)'
      }}>
        <h2 style={{ color: '#C54B42', marginBottom: '1rem' }}>
          Setting up your session...
        </h2>
        <p style={{ color: '#666' }}>
          Please wait while we complete the authentication process.
        </p>
        <div style={{ 
          marginTop: '1rem',
          fontSize: '2rem'
        }}>
          ⏳
        </div>
      </div>
    </div>
  );
};

export default AuthHandler;
