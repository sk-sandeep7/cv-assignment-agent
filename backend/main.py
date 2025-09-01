import os
import json
import io
import sys
import uuid
import datetime
import hmac
import hashlib
import base64
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import google.oauth2.credentials
import google_auth_oauthlib.flow

# Import database components
from database import database, question_assignments, metadata, engine

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, environment variables may not load from .env file")

# Add startup debugging
print("🚀 Starting application...")
print(f"Python version: {os.sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"PORT environment variable: {os.getenv('PORT', 'Not set')}")
print(f"SESSION_SECRET_KEY set: {'Yes' if os.getenv('SESSION_SECRET_KEY') else 'No'}")

# CRITICAL: Create client_secret.json IMMEDIATELY - inline execution
print("🔑 CRITICAL: Attempting to ensure client_secret.json exists...")
try:
    if os.path.exists('client_secret.json'):
        print("✅ client_secret.json file found")
    else:
        print("❌ client_secret.json file NOT found - creating from environment variables")
        
        # Try individual components first (most likely for Railway)
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
        
        if client_id and client_secret:
            print("✅ Found individual Google OAuth environment variables")
            client_config = {
                "web": {
                    "client_id": client_id,
                    "project_id": os.getenv('GOOGLE_PROJECT_ID', 'classroom-project-470618'),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": client_secret,
                    "redirect_uris": [f"https://{railway_domain}/api/auth/google/callback"] if railway_domain else ["http://localhost:8000/api/auth/google/callback"],
                    "javascript_origins": [f"https://{railway_domain}"] if railway_domain else ["http://localhost:8000"]
                }
            }
            try:
                with open('client_secret.json', 'w') as f:
                    json.dump(client_config, f, indent=2)
                print("✅ Created client_secret.json from individual environment variables")
            except Exception as e:
                print(f"❌ Error creating client_secret.json from components: {e}")
        else:
            # Try CLIENT_SECRET_JSON as backup
            client_secret_json = os.getenv('CLIENT_SECRET_JSON')
            if client_secret_json:
                print("✅ Found CLIENT_SECRET_JSON environment variable")
                try:
                    with open('client_secret.json', 'w') as f:
                        f.write(client_secret_json)
                    print("✅ Created client_secret.json from CLIENT_SECRET_JSON")
                except Exception as e:
                    print(f"❌ Error creating client_secret.json: {e}")
            else:
                print(f"⚠️ No valid OAuth configuration found!")
                print(f"GOOGLE_CLIENT_ID: {'SET' if client_id else 'NOT SET'}")
                print(f"GOOGLE_CLIENT_SECRET: {'SET' if client_secret else 'NOT SET'}")
                print(f"RAILWAY_PUBLIC_DOMAIN: {'SET' if railway_domain else 'NOT SET'}")
                print("⚠️ Application will continue but OAuth endpoints may fail")
except Exception as e:
    print(f"❌ Unexpected error creating client_secret.json: {e}")

try:
    print(f"Available files in current directory: {os.listdir('.')}")
except Exception as e:
    print(f"❌ Error listing directory: {e}")

try:
    import google.oauth2.credentials
    import google_auth_oauthlib.flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.auth.transport.requests import Request as GoogleRequest
    print("✅ Google API imports successful")
except ImportError as e:
    print(f"❌ Google API import failed: {e}")
    raise

try:
    from generate_openai import generate_questions_with_openai, generate_custom_question_with_openai
    from evaluation_openai import generate_evaluation_rubrics_with_openai
    from grade_openai import evaluate_submission, assign_grade_to_classroom
    print("✅ Local module imports successful")
except ImportError as e:
    print(f"❌ Local module import failed: {e}")
    print(f"Available files in current directory: {os.listdir('.')}")
    raise

# This line is crucial for local development. It allows OAuth to run over HTTP.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Temporary store for auth tokens (in production, use Redis or database)
AUTH_TOKENS = {}

# Long-term session tokens for localStorage-based authentication
SESSION_TOKENS = {}

def generate_auth_token(credentials_data):
    """Generate a temporary auth token for cross-domain authentication"""
    token_id = str(uuid.uuid4())
    AUTH_TOKENS[token_id] = {
        'credentials': credentials_data,
        'created_at': datetime.datetime.now(),
        'expires_at': datetime.datetime.now() + datetime.timedelta(minutes=5)  # 5 minute expiry
    }
    return token_id

def generate_session_token(credentials_data):
    """Generate a long-term session token for localStorage storage"""
    token_id = str(uuid.uuid4())
    SESSION_TOKENS[token_id] = {
        'credentials': credentials_data,
        'created_at': datetime.datetime.now(),
        'expires_at': datetime.datetime.now() + datetime.timedelta(days=7)  # 7 day expiry
    }
    return token_id

def get_credentials_from_session_token(token_id):
    """Retrieve credentials from long-term session token"""
    if token_id in SESSION_TOKENS:
        token_data = SESSION_TOKENS[token_id]
        if datetime.datetime.now() < token_data['expires_at']:
            return token_data['credentials']
        else:
            # Token expired, remove it
            del SESSION_TOKENS[token_id]
    return None

def get_credentials_from_token(token_id):
    """Retrieve credentials from temporary auth token"""
    if token_id in AUTH_TOKENS:
        token_data = AUTH_TOKENS[token_id]
        if datetime.datetime.now() < token_data['expires_at']:
            return token_data['credentials']
        else:
            # Token expired, remove it
            del AUTH_TOKENS[token_id]
    return None

# OAuth state utilities for stateless authentication
def create_signed_state(state: str, secret_key: str) -> str:
    """Create a signed state parameter that can be verified later"""
    message = state.encode('utf-8')
    signature = hmac.new(secret_key.encode('utf-8'), message, hashlib.sha256).hexdigest()
    signed_state = base64.b64encode(f"{state}:{signature}".encode('utf-8')).decode('utf-8')
    return signed_state

def verify_signed_state(signed_state: str, original_state: str, secret_key: str) -> bool:
    """Verify that the signed state matches the original state"""
    try:
        decoded = base64.b64decode(signed_state.encode('utf-8')).decode('utf-8')
        stored_state, signature = decoded.split(':', 1)
        
        # Verify the signature
        expected_signature = hmac.new(secret_key.encode('utf-8'), stored_state.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Check if signatures match and states match
        return hmac.compare_digest(signature, expected_signature) and stored_state == original_state
    except Exception:
        return False

app = FastAPI()

# Add startup event handler for debugging
@app.on_event("startup")
async def startup_event():
    """
    On application startup:
    1. Create the database table if it doesn't exist.
    2. Connect to the database.
    """
    print("🎯 FastAPI startup event triggered")
    print(f"Environment PYTHON_PATH: {os.getenv('PYTHONPATH', 'Not set')}")
    
    try:
        # Create the table if it doesn't exist
        metadata.create_all(engine)
        print("'question_assignments' table checked/created.")
        
        # Connect the database
        await database.connect()
        print("✅ Database connection successful")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    
    print("✅ Application startup completed successfully")

@app.on_event("shutdown")
async def shutdown():
    """
    On application shutdown:
    1. Disconnect from the database.
    """
    print("Application shutdown...")
    await database.disconnect()
    print("Database connection closed.")

# A secret key is required for SessionMiddleware to sign the cookies.
# Use environment variable for consistent sessions across restarts
SECRET_KEY = os.getenv('SESSION_SECRET_KEY', 'fallback-dev-key-change-in-production')
if SECRET_KEY == 'fallback-dev-key-change-in-production':
    print("⚠️ WARNING: Using default SECRET_KEY. Set SESSION_SECRET_KEY environment variable for production!")
else:
    print("✅ Using custom SESSION_SECRET_KEY from environment")

# Set session expiry to 7 days (7 * 24 * 60 * 60 seconds)
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds

# Configure session middleware with appropriate settings for Railway
is_production = os.getenv('RAILWAY_PUBLIC_DOMAIN') is not None
# For cross-site cookies (Vercel frontend → Railway backend), always use secure cookies in production
is_secure = is_production

print(f"🍪 Session middleware configuration:")
print(f"   SECRET_KEY length: {len(SECRET_KEY)}")
print(f"   SESSION_MAX_AGE: {SESSION_MAX_AGE} seconds")
print(f"   Production mode: {is_production}")
print(f"   Using secure cookies: {is_secure}")
print(f"   Same-site policy: {'none' if is_production else 'lax'}")
print(f"   Cross-site cookies enabled: {is_production}")

# For cross-site cookies to work properly, we need specific configuration
if is_production:
    # In production, cookie should be set for the backend domain (Railway)
    # but accessible from frontend domain (Vercel) via CORS
    session_config = {
        'secret_key': SECRET_KEY,
        'max_age': SESSION_MAX_AGE,
        'same_site': 'none',  # Required for cross-site requests
        'https_only': True,   # Required for SameSite=None
        'path': '/',          # Cookie available for all paths
        'domain': None        # Let Railway set its own domain
    }
else:
    # Local development configuration
    session_config = {
        'secret_key': SECRET_KEY,
        'max_age': SESSION_MAX_AGE,
        'same_site': 'lax',   # More permissive for local dev
        'https_only': False,  # HTTP allowed for local dev
        'path': '/',
        'domain': None
    }

print(f"   Final session config: {session_config}")

app.add_middleware(SessionMiddleware, **session_config)

# Allow CORS for frontend
# Get allowed origins from environment variable or use localhost for development
ALLOWED_ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", "https://cv-assignment-agent.vercel.app,http://localhost:5173,http://localhost:5174")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_RAW.split(",")]

# Debug logging for CORS configuration
print("="*50)
print("🔧 CORS DEBUG INFORMATION")
print("="*50)
print(f"Raw ALLOWED_ORIGINS env var: '{ALLOWED_ORIGINS_RAW}'")
print(f"Parsed ALLOWED_ORIGINS: {ALLOWED_ORIGINS}")
print(f"Number of allowed origins: {len(ALLOWED_ORIGINS)}")
for i, origin in enumerate(ALLOWED_ORIGINS):
    print(f"  [{i}]: '{origin}' (length: {len(origin)})")
print("="*50)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware for debugging requests
@app.middleware("http")
async def debug_requests(request: Request, call_next):
    # Log incoming request details
    origin = request.headers.get("origin", "No Origin Header")
    user_agent = request.headers.get("user-agent", "No User-Agent")[:50]
    
    print(f"🌐 Incoming Request:")
    print(f"   Method: {request.method}")
    print(f"   URL: {request.url}")
    print(f"   Origin: '{origin}'")
    print(f"   User-Agent: {user_agent}...")
    print(f"   Headers: {dict(request.headers)}")
    
    # Check if origin is in allowed list
    if origin != "No Origin Header":
        is_allowed = origin in ALLOWED_ORIGINS
        print(f"   ✅ Origin allowed: {is_allowed}")
        if not is_allowed:
            print(f"   ❌ Origin '{origin}' not in allowed list: {ALLOWED_ORIGINS}")
    
    response = await call_next(request)
    
    # Log response headers
    print(f"📤 Response Headers:")
    for header_name, header_value in response.headers.items():
        # Log CORS and Set-Cookie headers for debugging
        if 'access-control' in header_name.lower() or 'set-cookie' in header_name.lower():
            print(f"   {header_name}: {header_value}")
    print("-" * 50)
    
    return response

# --- Google API Configuration ---
CLIENT_SECRETS_FILE = os.getenv("CLIENT_SECRETS_FILE", "client_secret.json")
SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.students",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly",
    "https://www.googleapis.com/auth/drive.readonly"  # Added to access Google Drive files
]
API_SERVICE_NAME = 'classroom'
API_VERSION = 'v1'
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://cv-assignment-agent.vercel.app/home")  # Redirect to home page after login

# Note: Database setup is now handled in database.py
# Table will be created automatically during startup event

class QuestionRequest(BaseModel):
    topic: List[str]
    num_questions: int

class CriteriaRequest(BaseModel):
    question: str

class TaskRequest(BaseModel):
    question: str
    criteria: list

class RegenerateRequest(BaseModel):
    topic: list

class CustomQuestionRequest(BaseModel):
    user_input: str
    index: int

class EvaluationRubricRequest(BaseModel):
    question: str
    marks: int

class StoreQuestionsRequest(BaseModel):
    questions: List[Dict[str, Any]]

class EvaluationRequest(BaseModel):
    question: str
    marks: int

class AssignmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[str] = None  # Expecting ISO 8601 format
    course_id: str
    questions: List[Dict[str, Any]]

class GradeSubmissionsRequest(BaseModel):
    course_id: str
    assignment_id: str
    questions: List[Dict[str, Any]]

class QuestionIdsRequest(BaseModel):
    question_ids: List[str]

# --- Dependency for getting Classroom Service ---
async def get_classroom_service(request: Request):
    """
    FastAPI dependency to build and return a Google Classroom API service object.
    If the user is not authenticated, it raises an HTTPException.
    """
    credentials_dict = request.session.get('credentials')
    if not credentials_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # Check if session has expired (7 days)
    if 'login_timestamp' in credentials_dict:
        login_time = datetime.datetime.fromisoformat(credentials_dict['login_timestamp'])
        current_time = datetime.datetime.now()
        time_diff = current_time - login_time
        
        if time_diff.days >= 7:
            request.session.clear()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired after 7 days. Please log in again."
            )
    
    credentials = google.oauth2.credentials.Credentials(**{k: v for k, v in credentials_dict.items() if k != 'login_timestamp'})

    # If the token is expired, refresh it
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleRequest())
        # Update the session with the refreshed credentials, preserving login timestamp
        request.session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'login_timestamp': credentials_dict.get('login_timestamp')  # Preserve login timestamp
        }

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
        return service
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build Classroom service: {str(e)}"
        )

# --- Dependency for getting Drive Service ---
async def get_drive_service(request: Request):
    """
    FastAPI dependency to build and return a Google Drive API service object.
    If the user is not authenticated, it raises an HTTPException.
    """
    credentials_dict = request.session.get('credentials')
    if not credentials_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # Check if session has expired (7 days)
    if 'login_timestamp' in credentials_dict:
        login_time = datetime.datetime.fromisoformat(credentials_dict['login_timestamp'])
        current_time = datetime.datetime.now()
        time_diff = current_time - login_time
        
        if time_diff.days >= 7:
            request.session.clear()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired after 7 days. Please log in again."
            )
    
    credentials = google.oauth2.credentials.Credentials(**{k: v for k, v in credentials_dict.items() if k != 'login_timestamp'})

    # If the token is expired, refresh it
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleRequest())
        # Update the session with the refreshed credentials, preserving login timestamp
        request.session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'login_timestamp': credentials_dict.get('login_timestamp')  # Preserve login timestamp
        }

    try:
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build Google API service: {e}"
        )

@app.get("/")
def read_root():
    """Root endpoint for health check"""
    return {
        "status": "healthy", 
        "message": "CV Assignment Agent API is running",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0.2"
    }

@app.get("/debug/session-config")
def debug_session_config():
    """Debug endpoint to check session configuration"""
    return {
        "message": "Session Configuration Debug",
        "session_secret_key_set": bool(os.getenv('SESSION_SECRET_KEY')),
        "session_secret_key_length": len(os.getenv('SESSION_SECRET_KEY', '')),
        "session_max_age": SESSION_MAX_AGE,
        "is_production": os.getenv('RAILWAY_PUBLIC_DOMAIN') is not None,
        "railway_domain": os.getenv('RAILWAY_PUBLIC_DOMAIN', 'Not set'),
        "environment_vars": {
            "RAILWAY_PUBLIC_DOMAIN": os.getenv('RAILWAY_PUBLIC_DOMAIN', 'Not set'),
            "ALLOWED_ORIGINS": os.getenv("ALLOWED_ORIGINS", "Not set"),
            "SESSION_SECRET_KEY": "SET" if os.getenv('SESSION_SECRET_KEY') else "NOT SET"
        }
    }

@app.get("/debug/cors")
def debug_cors_info(request: Request):
    """Debug endpoint to check CORS configuration"""
    origin = request.headers.get("origin", "No Origin Header")
    return {
        "message": "CORS Debug Information",
        "request_origin": origin,
        "allowed_origins": ALLOWED_ORIGINS,
        "is_origin_allowed": origin in ALLOWED_ORIGINS if origin != "No Origin Header" else False,
        "cors_headers_should_be_present": True,
        "environment_variable": os.getenv("ALLOWED_ORIGINS", "NOT SET"),
        "total_allowed_origins": len(ALLOWED_ORIGINS)
    }

@app.options("/api/auth/google/url")
async def preflight_google_auth():
    """Handle preflight requests for Google auth endpoint"""
    return {"message": "Preflight OK"}

@app.options("/debug/cors")
async def preflight_debug_cors():
    """Handle preflight requests for debug endpoint"""
    return {"message": "Preflight OK"}

# --- Google OAuth and Classroom API Routes ---

@app.get("/api/auth/google/url")
async def get_google_auth_url(request: Request):
    """Provides the Google OAuth 2.0 URL to the frontend."""
    try:
        print(f"🔑 Auth URL request - CLIENT_SECRETS_FILE: {CLIENT_SECRETS_FILE}")
        print(f"🔑 File exists: {os.path.exists(CLIENT_SECRETS_FILE)}")
        
        if not os.path.exists(CLIENT_SECRETS_FILE):
            print(f"❌ {CLIENT_SECRETS_FILE} not found!")
            print(f"Available files: {os.listdir('.')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Client secrets file not found: {CLIENT_SECRETS_FILE}"
            )
        
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES)
        
        # Generate the redirect URI - force HTTPS for Railway deployment
        railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
        if railway_domain:
            # For Railway deployment, always use HTTPS
            redirect_uri = f"https://{railway_domain}/api/auth/google/callback"
        else:
            # For local development
            redirect_uri = request.url_for('api_auth_google_callback')
        
        flow.redirect_uri = redirect_uri
        
        print(f"🔑 Redirect URI: {redirect_uri}")
        print(f"🔑 Railway domain: {railway_domain}")
        print(f"🔑 Using forced HTTPS: {railway_domain is not None}")

        authorization_url, state = flow.authorization_url(
            access_type='offline', include_granted_scopes='true')
        
        # Create a signed state token instead of storing in session
        signed_state = create_signed_state(state, SECRET_KEY)
        
        # Store the signed state in the URL instead of session
        authorization_url = authorization_url.replace(f"state={state}", f"state={signed_state}")
        
        print(f"🔑 Auth URL generated successfully")
        print(f"🔑 Original state: {state}")
        print(f"🔑 Signed state: {signed_state}")
        print(f"🔑 Using stateless OAuth flow")
        return JSONResponse({'auth_url': authorization_url})
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Auth URL generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auth URL: {str(e)}"
        )

@app.get("/api/auth/google/callback")
async def api_auth_google_callback(request: Request):
    """Handles the callback from Google after the user has authenticated."""
    signed_state_from_query = request.query_params.get('state')
    
    print(f"🔑 OAuth Callback Debug (Stateless):")
    print(f"   Signed state from query: {signed_state_from_query}")
    print(f"   Full URL: {request.url}")
    print(f"   Request cookies: {request.cookies}")
    
    if not signed_state_from_query:
        print(f"❌ No state parameter in callback!")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing state parameter")

    try:
        # Decode the signed state to get the original state
        decoded = base64.b64decode(signed_state_from_query.encode('utf-8')).decode('utf-8')
        original_state, signature = decoded.split(':', 1)
        
        # Verify the signature
        expected_signature = hmac.new(SECRET_KEY.encode('utf-8'), original_state.encode('utf-8'), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            print(f"❌ Invalid state signature!")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state signature")
        
        print(f"✅ State signature verified successfully")
        print(f"   Original state: {original_state}")
        
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, state=original_state)
        
        # Use the same redirect URI logic as in auth URL generation
        railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
        if railway_domain:
            # For Railway deployment, always use HTTPS
            redirect_uri = f"https://{railway_domain}/api/auth/google/callback"
        else:
            # For local development
            redirect_uri = request.url_for('api_auth_google_callback')
        
        flow.redirect_uri = redirect_uri
        print(f"🔑 Callback redirect URI: {redirect_uri}")

        # Create a clean authorization response URL with the original state
        # Parse the current URL and replace the state parameter
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        parsed_url = urlparse(str(request.url))
        query_params = parse_qs(parsed_url.query)
        
        # Replace the signed state with the original state
        query_params['state'] = [original_state]
        
        # Reconstruct the URL with the original state
        new_query = urlencode(query_params, doseq=True)
        authorization_response = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        
        print(f"🔑 Reconstructed auth response URL with original state for token exchange")
        
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        
        # Store credentials in session (keep for backward compatibility)
        credentials_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'login_timestamp': datetime.datetime.now().isoformat()
        }
        
        request.session['credentials'] = credentials_data
        
        print(f"🔑 Session created - Session keys: {list(request.session.keys())}")
        print(f"🔑 Session created - Has credentials: {'credentials' in request.session}")
        print(f"🔑 Session created - Request origin: {request.headers.get('origin', 'No origin')}")
        print(f"🔑 Session created - Request host: {request.headers.get('host', 'No host')}")
        
        # Create temporary auth token for cross-domain authentication
        auth_token = generate_auth_token(credentials_data)
        print(f"🔑 Generated temporary auth token: {auth_token}")
        
        # Redirect with auth token
        frontend_url_with_token = f"{FRONTEND_URL}?auth_token={auth_token}"
        response = RedirectResponse(url=frontend_url_with_token)
        
        # Debug: Check what cookies will be set
        print(f"🔑 Response redirect URL: {frontend_url_with_token}")
        print(f"🔑 Response headers will include session cookie")
        print(f"🔑 Redirecting with temporary auth token")
        return response
        
    except Exception as e:
        print(f"❌ OAuth callback error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': "An error occurred during token exchange", 'details': str(e)}
        )

@app.post("/api/auth/create-session-token")
async def create_session_token(request: Request):
    """Create a long-term session token for localStorage-based authentication"""
    data = await request.json()
    auth_token = data.get('auth_token')
    
    if not auth_token:
        raise HTTPException(status_code=400, detail="Auth token required")
    
    credentials_data = get_credentials_from_token(auth_token)
    if not credentials_data:
        raise HTTPException(status_code=400, detail="Invalid or expired auth token")
    
    # Create long-term session token
    session_token = generate_session_token(credentials_data)
    
    # Also set session cookie as backup
    request.session['credentials'] = credentials_data
    
    # Remove the used auth token
    if auth_token in AUTH_TOKENS:
        del AUTH_TOKENS[auth_token]
    
    print(f"🔑 Created session token: {session_token}")
    return JSONResponse({
        'status': 'success', 
        'session_token': session_token,
        'message': 'Session token created successfully'
    })

@app.post("/api/auth/verify-session-token")
async def verify_session_token(request: Request):
    """Verify session token and return authentication status"""
    data = await request.json()
    session_token = data.get('session_token')
    
    if not session_token:
        return JSONResponse({'logged_in': False, 'message': 'No session token provided'})
    
    credentials_data = get_credentials_from_session_token(session_token)
    if not credentials_data:
        return JSONResponse({'logged_in': False, 'message': 'Invalid or expired session token'})
    
    # Refresh the session cookie
    request.session['credentials'] = credentials_data
    
    print(f"🔑 Session token verified successfully")
    return JSONResponse({'logged_in': True, 'message': 'Session token valid'})

@app.post("/api/auth/exchange-token")
async def exchange_auth_token(request: Request):
    """Exchange temporary auth token for session credentials"""
    data = await request.json()
    auth_token = data.get('auth_token')
    
    if not auth_token:
        raise HTTPException(status_code=400, detail="Auth token required")
    
    credentials_data = get_credentials_from_token(auth_token)
    if not credentials_data:
        raise HTTPException(status_code=400, detail="Invalid or expired auth token")
    
    # Set up session with credentials
    request.session['credentials'] = credentials_data
    
    # Remove the used token
    if auth_token in AUTH_TOKENS:
        del AUTH_TOKENS[auth_token]
    
    print(f"🔑 Token exchanged successfully - User now authenticated")
    return JSONResponse({'status': 'success', 'message': 'Authentication established'})

@app.post("/api/auth/google/logout")
async def api_auth_google_logout(request: Request):
    """Logs the user out by clearing the session."""
    request.session.clear()
    return JSONResponse({'status': 'success', 'message': 'Logged out'})

@app.get("/api/check_auth")
async def api_check_auth(request: Request):
    """Checks if a user's session and credentials exist and haven't expired."""
    # Enhanced debugging for session issues
    origin = request.headers.get("origin", "No Origin")
    user_agent = request.headers.get("user-agent", "No User-Agent")[:50]
    
    print(f"🔐 Auth check - Request details:")
    print(f"   Origin: {origin}")
    print(f"   User-Agent: {user_agent}...")
    print(f"   Cookie header: {request.headers.get('cookie', 'No Cookie Header')}")
    print(f"   Session keys: {list(request.session.keys())}")
    print(f"   Has credentials: {'credentials' in request.session}")
    print(f"   Session ID: {request.session.get('_session_id', 'No ID')}")
    print(f"   All cookies: {dict(request.cookies)}")
    
    if 'credentials' in request.session:
        credentials_dict = request.session['credentials']
        
        # Check if login timestamp exists and if session has expired (7 days)
        if 'login_timestamp' in credentials_dict:
            login_time = datetime.datetime.fromisoformat(credentials_dict['login_timestamp'])
            current_time = datetime.datetime.now()
            time_diff = current_time - login_time
            
            print(f"🔐 Session age: {time_diff.days} days, {time_diff.seconds} seconds")
            
            # If more than 7 days have passed, clear session and return logged out
            if time_diff.days >= 7:
                print(f"🔐 Session expired after 7 days - clearing session")
                request.session.clear()
                return JSONResponse({'logged_in': False, 'message': 'Session expired after 7 days'})
        
        print(f"🔐 Auth check - User is authenticated ✅")
        return JSONResponse({'logged_in': True})
    
    print(f"🔐 Auth check - User is NOT authenticated ❌")
    return JSONResponse({'logged_in': False, 'message': 'No session found'})

@app.get("/api/classroom/courses")
async def api_get_courses(service=Depends(get_classroom_service)):
    """Fetches the list of courses for the authenticated user."""
    try:
        print("Fetching courses...")
        results = service.courses().list(teacherId="me", pageSize=50).execute()
        courses = results.get('courses', [])
        print(f"Found {len(courses)} courses")
        for course in courses:
            print(f"Course: {course.get('name')} (ID: {course.get('id')})")
        return JSONResponse(content=courses)
    except HttpError as error:
        print(f"HTTP Error in courses endpoint: {error}")
        print(f"Error details: {error.content}")
        raise HTTPException(status_code=error.resp.status, detail=f"An API error occurred: {error}")
    except Exception as e:
        print(f"General error in courses endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/classroom/create-assignment")
async def api_create_assignment(assignment_data: AssignmentCreate, service=Depends(get_classroom_service)):
    """Creates a new assignment (courseWork) in a specific course."""
    
    # Format the description with questions and marks
    description_parts = []
    topic_str = ""
    
    if assignment_data.questions:
        # Extract topic from first question for title
        if assignment_data.questions[0].get('topic'):
            if isinstance(assignment_data.questions[0]['topic'], list):
                topic_str = ", ".join(assignment_data.questions[0]['topic'])
            else:
                topic_str = str(assignment_data.questions[0]['topic'])
    
    # Create title
    title = f"Assignment-{topic_str}" if topic_str else assignment_data.title
    
    # Format questions in description
    total_marks = 0
    for i, q in enumerate(assignment_data.questions, 1):
        question_text = q.get('question', '')
        marks = q.get('marks', 0)
        question_id = q.get('id', '')
        
        # Add to total marks
        total_marks += marks
        
        # Include question ID in the format {id: xxxx}
        if question_id:
            description_parts.append(f"Q{i}. {question_text} ({marks} marks) {{id: {question_id}}}")
        else:
            description_parts.append(f"Q{i}. {question_text} ({marks} marks)")
    
    description = "\n\n".join(description_parts)
    if assignment_data.description:
        description = f"{assignment_data.description}\n\n{description}"
    
    print(f"Creating assignment with total marks: {total_marks}")
    
    course_work = {
        'title': title,
        'description': description,
        'workType': 'ASSIGNMENT',
        'state': 'PUBLISHED',
        'maxPoints': total_marks  # Set as graded assignment with total marks
    }

    # Handle the deadline if it was provided in the request
    if assignment_data.deadline:
        try:
            # Parse the ISO 8601 string from the frontend.
            dt_deadline = datetime.datetime.fromisoformat(assignment_data.deadline.replace("Z", "+00:00"))
            
            # Convert to UTC to ensure timezone consistency for the API.
            dt_utc = dt_deadline.astimezone(datetime.timezone.utc)
            
            # Format for the Google Classroom API
            course_work['dueDate'] = {
                'year': dt_utc.year,
                'month': dt_utc.month,
                'day': dt_utc.day
            }
            course_work['dueTime'] = {
                'hours': dt_utc.hour,
                'minutes': dt_utc.minute
            }
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid deadline format. Please use ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SSZ)."
            )
            
    try:
        assignment = service.courses().courseWork().create(
            courseId=assignment_data.course_id,
            body=course_work
        ).execute()
        return JSONResponse(content=assignment)
    except HttpError as error:
        error_details = json.loads(error.content.decode('utf-8'))
        raise HTTPException(
            status_code=error.resp.status,
            detail={"message": "An API error occurred", "details": error_details}
        )

@app.get("/api/classroom/assignments/{course_id}")
async def api_get_assignments(course_id: str, service=Depends(get_classroom_service)):
    """Fetches the list of assignments (courseWork) for a specific course."""
    try:
        print(f"Fetching assignments for course: {course_id}")
        results = service.courses().courseWork().list(
            courseId=course_id,
            pageSize=50
        ).execute()
        assignments = results.get('courseWork', [])
        print(f"Found {len(assignments)} assignments")
        return JSONResponse(content=assignments)
    except HttpError as error:
        print(f"HTTP Error in assignments endpoint: {error}")
        print(f"Error details: {error.content}")
        raise HTTPException(status_code=error.resp.status, detail=f"An API error occurred: {error}")
    except Exception as e:
        print(f"General error in assignments endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/classroom/submissions/{course_id}/{assignment_id}")
async def api_get_submissions(course_id: str, assignment_id: str, service=Depends(get_classroom_service)):
    """Fetches student submissions for a specific assignment."""
    try:
        print(f"Fetching submissions for course: {course_id}, assignment: {assignment_id}")
        
        # Get submissions
        submissions_result = service.courses().courseWork().studentSubmissions().list(
            courseId=course_id,
            courseWorkId=assignment_id,
            pageSize=100
        ).execute()
        submissions = submissions_result.get('studentSubmissions', [])
        print(f"Found {len(submissions)} submissions")
        
        # Get course roster to map user IDs to names
        try:
            students_result = service.courses().students().list(
                courseId=course_id,
                pageSize=100
            ).execute()
            students = students_result.get('students', [])
            print(f"Found {len(students)} students in course")
            
            # Debug: Print the structure of the first student (if any)
            if students:
                print(f"Sample student structure: {students[0]}")
                
        except HttpError as student_error:
            print(f"Error fetching students: {student_error}")
            # If we can't get students, continue with submissions but without names
            students = []
        
        # Create a mapping of userId to student info
        student_map = {}
        for student in students:
            try:
                # Get student profile information with fallbacks
                profile = student.get('profile', {})
                name_info = profile.get('name', {})
                
                # Try different ways to get the student name
                full_name = name_info.get('fullName')
                if not full_name:
                    given_name = name_info.get('givenName', '')
                    family_name = name_info.get('familyName', '')
                    full_name = f"{given_name} {family_name}".strip()
                
                if not full_name:
                    full_name = f"Student {student.get('userId', 'Unknown')}"
                
                # Note: Google Classroom API doesn't provide email addresses in the students.list endpoint
                # This is by design for privacy reasons. Email access would require additional permissions
                # and possibly a different API endpoint or admin access.
                student_id = student.get('userId', 'Unknown')
                
                student_map[student['userId']] = {
                    'name': full_name,
                    'email': f"Student ID: {student_id}",  # Show student ID instead of email
                    'studentId': student_id
                }
                print(f"Processed student: {full_name} (ID: {student_id})")
                
            except Exception as e:
                print(f"Unexpected error processing student: {e}")
                print(f"Student data: {student}")
                # Still add student with minimal info
                student_id = student.get('userId', 'unknown')
                student_map[student_id] = {
                    'name': f"Student {student_id}",
                    'email': f"Student ID: {student_id}",
                    'studentId': student_id
                }
                continue
        
        # Enhance submissions with student information and attachments
        enhanced_submissions = []
        for submission in submissions:
            student_info = student_map.get(submission['userId'], {
                'name': 'Unknown Student',
                'email': f"Student ID: {submission['userId']}",
                'studentId': submission['userId']
            })
            
            # Extract attachment information
            attachments = []
            assignment_submission = submission.get('assignmentSubmission', {})
            
            # Check for different types of attachments
            if 'attachments' in assignment_submission:
                for attachment in assignment_submission['attachments']:
                    attachment_info = {}
                    
                    # Handle Google Drive files
                    if 'driveFile' in attachment:
                        drive_file = attachment['driveFile']
                        attachment_info = {
                            'type': 'drive_file',
                            'id': drive_file.get('id'),
                            'title': drive_file.get('title', 'Untitled'),
                            'alternateLink': drive_file.get('alternateLink'),
                            'thumbnailUrl': drive_file.get('thumbnailUrl'),
                            'downloadUrl': drive_file.get('alternateLink')  # Use alternate link for viewing
                        }
                        
                    # Handle YouTube videos
                    elif 'youTubeVideo' in attachment:
                        youtube_video = attachment['youTubeVideo']
                        attachment_info = {
                            'type': 'youtube_video',
                            'id': youtube_video.get('id'),
                            'title': youtube_video.get('title', 'YouTube Video'),
                            'alternateLink': youtube_video.get('alternateLink'),
                            'thumbnailUrl': youtube_video.get('thumbnailUrl'),
                            'downloadUrl': None
                        }
                        
                    # Handle links
                    elif 'link' in attachment:
                        link = attachment['link']
                        attachment_info = {
                            'type': 'link',
                            'url': link.get('url'),
                            'title': link.get('title', 'Link'),
                            'thumbnailUrl': link.get('thumbnailUrl'),
                            'downloadUrl': link.get('url')
                        }
                    
                    if attachment_info:
                        attachments.append(attachment_info)
            
            enhanced_submission = {
                'id': submission['id'],
                'userId': submission['userId'],
                'studentName': student_info['name'],
                'studentEmail': student_info['email'],  # This will now show "Student ID: ..." instead of email
                'studentId': student_info.get('studentId', submission['userId']),
                'state': submission['state'],
                'creationTime': submission.get('creationTime'),
                'updateTime': submission.get('updateTime'),
                'assignedGrade': submission.get('assignedGrade'),
                'draftGrade': submission.get('draftGrade'),
                'submissionHistory': submission.get('submissionHistory', []),
                'attachments': attachments
            }
            enhanced_submissions.append(enhanced_submission)
        
        print(f"Returning {len(enhanced_submissions)} enhanced submissions")
        return JSONResponse(content=enhanced_submissions)
    except HttpError as error:
        print(f"HTTP Error in submissions endpoint: {error}")
        print(f"Error details: {error.content}")
        raise HTTPException(status_code=error.resp.status, detail=f"An API error occurred: {error}")
    except Exception as e:
        print(f"General error in submissions endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/download/drive-file/{file_id}")
async def download_drive_file(file_id: str, drive_service=Depends(get_drive_service)):
    """Download a PDF file from Google Drive."""
    try:
        print(f"Attempting to download Drive file: {file_id}")
        
        # Get file metadata first
        file_metadata = drive_service.files().get(fileId=file_id).execute()
        file_name = file_metadata.get('name', 'download.pdf')
        mime_type = file_metadata.get('mimeType', 'application/pdf')
        
        print(f"File metadata: {file_name}, {mime_type}")
        
        # Download file content
        request = drive_service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = request.execute()
        
        if isinstance(downloader, bytes):
            file_content.write(downloader)
        else:
            # Handle case where it's a file-like object
            file_content.write(downloader)
        
        file_content.seek(0)
        
        # Set appropriate headers for PDF download
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Content-Type': mime_type
        }
        
        return StreamingResponse(
            io.BytesIO(file_content.read()),
            media_type=mime_type,
            headers=headers
        )
        
    except HttpError as error:
        print(f"HTTP Error downloading file: {error}")
        if error.resp.status == 404:
            raise HTTPException(status_code=404, detail="File not found")
        elif error.resp.status == 403:
            raise HTTPException(status_code=403, detail="Access denied to file")
        else:
            raise HTTPException(status_code=error.resp.status, detail=f"Drive API error: {error}")
    except Exception as e:
        print(f"General error downloading file: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/get-questions-by-ids")
async def get_questions_by_ids(request: Request):
    """
    Get stored questions by their IDs for more precise assignment-question matching
    """
    if not database.is_connected:
        raise HTTPException(
            status_code=503, detail="Database connection is not available."
        )
    
    try:
        data = await request.json()
        question_ids = data.get('question_ids', [])
        
        if not question_ids:
            return {
                "status": "error",
                "message": "No question IDs provided"
            }
        
        print(f"🔍 Searching for questions with IDs: {question_ids}")
        
        # Query PostgreSQL with IN clause
        query = question_assignments.select().where(
            question_assignments.c.id.in_(question_ids)
        ).order_by(question_assignments.c.created_at.desc())
        
        results = await database.fetch_all(query)
        
        questions = []
        for row in results:
            questions.append({
                'id': row["id"],
                'question': row["question"],
                'marks': row["marks"],
                'topic': row["topic"],  # Already JSON from PostgreSQL
                'rubrics': row["evaluation_rubrics"]  # Already JSON from PostgreSQL
            })
        
        print(f"✅ Found {len(questions)} questions by ID")
        for q in questions:
            print(f"   - ID: {q['id']}, Question: {q['question'][:50]}...")
        
        return {
            'status': 'success',
            'questions': questions
        }
        
    except Exception as e:
        print(f"❌ Error fetching questions by IDs: {e}")
        return {
            'status': 'error',
            'message': f'Error fetching questions: {str(e)}'
        }


@app.get("/api/get-assignment-questions/{assignment_title}")
async def get_assignment_questions(assignment_title: str):
    """
    Get stored questions for an assignment based on the assignment title.
    This helps fetch evaluation criteria for grading (fallback method).
    """
    if not database.is_connected:
        raise HTTPException(
            status_code=503, detail="Database connection is not available."
        )
    
    try:
        print(f"🔍 Fallback: Searching questions by assignment title: {assignment_title}")
        
        # Extract topic from assignment title (format: "Assignment-{topic}")
        if assignment_title.startswith("Assignment-"):
            topic = assignment_title.replace("Assignment-", "")
            
            print(f"🔍 Extracted topic from title: {topic}")
            
            # Search for questions with matching topic using PostgreSQL JSON contains
            # Note: Using text search on JSON field since topic might be an array
            query = question_assignments.select().where(
                question_assignments.c.topic.astext.contains(topic)
            ).order_by(question_assignments.c.created_at.desc())
            
            results = await database.fetch_all(query)
            
            questions = []
            for row in results:
                questions.append({
                    'id': row["id"],
                    'question': row["question"],
                    'marks': row["marks"],
                    'topic': row["topic"],  # Already JSON from PostgreSQL
                    'rubrics': row["evaluation_rubrics"]  # Already JSON from PostgreSQL
                })
            
            print(f"✅ Fallback method found {len(questions)} questions")
            for q in questions:
                print(f"   - ID: {q['id']}, Question: {q['question'][:50]}...")
            
            return JSONResponse(content={
                'status': 'success',
                'questions': questions
            })
        else:
            return JSONResponse(content={
                'status': 'error',
                'message': 'Invalid assignment title format'
            })
            
    except Exception as e:
        print(f"Error fetching assignment questions: {e}")
        return JSONResponse(content={
            'status': 'error',
            'message': f'Error fetching questions: {str(e)}'
        })

@app.post("/api/classroom/grade-submissions")
async def api_grade_submissions(
    request: GradeSubmissionsRequest,
    classroom_service=Depends(get_classroom_service),
    drive_service=Depends(get_drive_service)
):
    """
    Grade student submissions using LLM evaluation against rubrics.
    Automatically assigns grades back to Google Classroom.
    """
    try:
        print(f"Starting grading for assignment {request.assignment_id} in course {request.course_id}")
        
        # Get all submissions for this assignment
        submissions_result = classroom_service.courses().courseWork().studentSubmissions().list(
            courseId=request.course_id,
            courseWorkId=request.assignment_id,
            pageSize=100
        ).execute()
        
        submissions = submissions_result.get('studentSubmissions', [])
        print(f"Found {len(submissions)} submissions to grade")
        
        # Get student information for names
        student_map = {}
        try:
            students_result = classroom_service.courses().students().list(
                courseId=request.course_id,
                pageSize=100
            ).execute()
            students = students_result.get('students', [])
            
            for student in students:
                profile = student.get('profile', {})
                name_info = profile.get('name', {})
                full_name = name_info.get('fullName', f"Student {student.get('userId', 'Unknown')}")
                student_map[student['userId']] = full_name
        except Exception as e:
            print(f"Error fetching student names: {e}")
        
        graded_results = []
        successful_grades = 0
        
        for submission in submissions:
            try:
                # Skip if not turned in
                if submission.get('state') != 'TURNED_IN':
                    print(f"Skipping submission {submission.get('id')} - not turned in")
                    continue
                
                student_id = submission.get('userId')
                student_name = student_map.get(student_id, f"Student {student_id}")
                
                print(f"Grading submission from {student_name}")
                
                # Evaluate the submission
                grading_result = await evaluate_submission(
                    submission_data=submission,
                    questions=request.questions,
                    drive_service=drive_service,
                    student_name=student_name
                )
                
                if grading_result:
                    # Assign grade back to Google Classroom
                    assigned_grade = grading_result.get('total_marks', 0)
                    feedback = grading_result.get('overall_feedback', '')
                    
                    grade_assigned = await assign_grade_to_classroom(
                        classroom_service=classroom_service,
                        course_id=request.course_id,
                        assignment_id=request.assignment_id,
                        submission_id=submission.get('id'),
                        assigned_grade=assigned_grade,
                        feedback=feedback
                    )
                    
                    if grade_assigned:
                        successful_grades += 1
                        grading_result['grade_assigned_to_classroom'] = True
                    else:
                        grading_result['grade_assigned_to_classroom'] = False
                    
                    graded_results.append({
                        'student_id': student_id,
                        'student_name': student_name,
                        'submission_id': submission.get('id'),
                        'grading_result': grading_result
                    })
                else:
                    print(f"Failed to grade submission from {student_name}")
                    
            except Exception as e:
                print(f"Error processing submission from {student_name}: {e}")
                continue
        
        return JSONResponse(content={
            'status': 'success',
            'total_submissions': len(submissions),
            'graded_count': len(graded_results),
            'grades_assigned_to_classroom': successful_grades,
            'results': graded_results
        })
        
    except HttpError as error:
        print(f"Google Classroom API error: {error}")
        raise HTTPException(
            status_code=error.resp.status,
            detail=f"Google Classroom API error: {error}"
        )
    except Exception as e:
        print(f"Error in grading endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error grading submissions: {str(e)}"
        )

# --- Existing Question Generation Routes ---

@app.post("/api/generate-questions")
async def generate_questions(request: Request):
    data = await request.json()
    user_topics = data.get("topic", [])
    num_questions = int(data.get("num_questions", 3))

    get_few_shots = generate_questions_with_openai(user_topics, num_questions)

    # Enforce the number of questions
    if len(get_few_shots) > num_questions:
        get_few_shots = get_few_shots[:num_questions]
        
    questions = [
        {"question": q["question"], "marks": q.get("marks", 7), "topic": q.get("topic", [])} for q in get_few_shots
    ]
    
    # Note: Questions are not saved to DB here anymore
    # They will be saved only when user clicks "Proceed" button
    return {"questions": questions}

@app.post("/api/get-evaluation-criteria")
def get_criteria(req: CriteriaRequest):
    # Example: return static criteria
    criteria = [
        "Clarity and accuracy of explanation.",
        "Depth of understanding demonstrated.",
        "Use of relevant examples."
    ]
    return {"criteria": criteria}

@app.post("/api/execute-task")
def execute_task(req: TaskRequest):
    # Example: just return success
    return {"status": "success", "message": "Task completed successfully."}


@app.post("/api/generate-evaluation-rubrics")
async def generate_evaluation_rubrics(req: EvaluationRequest):
    question_with_marks = f"{req.question} ({req.marks} marks)"
    rubrics = generate_evaluation_rubrics_with_openai(question_with_marks)
    if rubrics:
        return rubrics
    return {}


@app.post("/api/generate-custom-question")
async def generate_custom_question(req: CustomQuestionRequest):
    user_input = req.user_input
    new_question_data = generate_custom_question_with_openai(user_input)
    if new_question_data:
        return new_question_data
    return {}


@app.post("/api/regenerate-question")
async def regenerate_question(request: Request):
    data = await request.json()
    user_topics = data.get("topic", [])
    get_few_shots = generate_questions_with_openai(user_topics, 1)
    if get_few_shots:
        new_question = {
            "question": get_few_shots[0]["question"],
            "marks": get_few_shots[0].get("marks", 7),
            "topic": get_few_shots[0].get("topic", [])
        }
        return new_question
    return {}


@app.post("/api/store-questions")
async def store_questions(req: StoreQuestionsRequest):
    """
    Store all questions with their evaluation rubrics in the database
    Called when user clicks the Proceed button
    """
    if not database.is_connected:
        raise HTTPException(
            status_code=503, detail="Database connection is not available."
        )
    
    try:
        stored_questions = []
        
        for question_data in req.questions:
            # Generate unique ID using timestamp and UUID
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = f"{timestamp}_{str(uuid.uuid4())[:8]}"
            
            # Extract data from the question
            question_text = question_data.get("question", "")
            marks = question_data.get("marks", 0)
            topic = question_data.get("topic", [])  # Store as JSON directly
            evaluation_rubrics = question_data.get("rubrics", [])  # Store as JSON directly
            
            # Insert into database using PostgreSQL
            query = question_assignments.insert().values(
                id=unique_id,
                question=question_text,
                marks=marks,
                topic=topic,
                evaluation_rubrics=evaluation_rubrics
            )
            
            await database.execute(query)
            
            print(f"✅ Successfully stored question with ID: {unique_id} - Question: {question_text[:50]}...")
            
            stored_questions.append({
                "id": unique_id,
                "question": question_text,
                "marks": marks,
                "topic": topic,
                "rubrics": evaluation_rubrics
            })
        
        return {
            "status": "success",
            "message": f"Successfully stored {len(stored_questions)} questions",
            "stored_questions": stored_questions
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to store questions: {str(e)}"
        }


@app.get("/api/get-stored-questions")
async def get_stored_questions():
    """
    Retrieve all stored questions from the database
    """
    if not database.is_connected:
        raise HTTPException(
            status_code=503, detail="Database connection is not available."
        )
    
    try:
        query = question_assignments.select().order_by(question_assignments.c.created_at.desc())
        rows = await database.fetch_all(query)
        
        questions = []
        for row in rows:
            questions.append({
                "id": row["id"],
                "question": row["question"],
                "marks": row["marks"],
                "topic": row["topic"],  # Already JSON from PostgreSQL
                "rubrics": row["evaluation_rubrics"],  # Already JSON from PostgreSQL
                "created_at": row["created_at"]
            })
        
        return {
            "status": "success",
            "questions": questions
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve questions: {str(e)}"
        }
