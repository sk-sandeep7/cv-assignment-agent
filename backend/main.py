import os
import json
import io
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
import sqlite3
import uuid
import datetime
from typing import List, Dict, Any, Optional

# Add startup debugging
print("🚀 Starting application...")
print(f"Python version: {os.sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"PORT environment variable: {os.getenv('PORT', 'Not set')}")

# Check for client_secret.json file and create if needed
def ensure_client_secret_file():
    """Ensure client_secret.json exists, create from env vars if needed"""
    try:
        if os.path.exists('client_secret.json'):
            print("✅ client_secret.json file found")
            try:
                with open('client_secret.json', 'r') as f:
                    secret_data = json.load(f)
                    print(f"✅ client_secret.json is valid JSON with keys: {list(secret_data.keys())}")
                return True
            except Exception as e:
                print(f"❌ Error reading client_secret.json: {e}")
                return False
        else:
            print("❌ client_secret.json file NOT found - creating from environment variables")
            # Create client_secret.json from environment variables
            client_secret_json = os.getenv('CLIENT_SECRET_JSON')
            if client_secret_json:
                print("✅ Found CLIENT_SECRET_JSON environment variable")
                try:
                    with open('client_secret.json', 'w') as f:
                        f.write(client_secret_json)
                    print("✅ Created client_secret.json from CLIENT_SECRET_JSON")
                    return True
                except Exception as e:
                    print(f"❌ Error creating client_secret.json: {e}")
                    return False
            else:
                # Try individual components
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
                        return True
                    except Exception as e:
                        print(f"❌ Error creating client_secret.json from components: {e}")
                        return False
                else:
                    print(f"⚠️ No valid OAuth configuration found!")
                    print(f"GOOGLE_CLIENT_ID: {'SET' if client_id else 'NOT SET'}")
                    print(f"GOOGLE_CLIENT_SECRET: {'SET' if client_secret else 'NOT SET'}")
                    print(f"RAILWAY_PUBLIC_DOMAIN: {'SET' if railway_domain else 'NOT SET'}")
                    print("⚠️ Application will continue but OAuth endpoints may fail")
                    return False
    except Exception as e:
        print(f"❌ Unexpected error in ensure_client_secret_file: {e}")
        return False

# Try to ensure client secret file exists (non-fatal)
print("🔑 Attempting to ensure client_secret.json exists...")
client_secret_ok = ensure_client_secret_file()
if not client_secret_ok:
    print("⚠️ OAuth configuration incomplete - some features may not work")

print(f"Available files in current directory: {os.listdir('.')}")

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

app = FastAPI()

# Add startup event handler for debugging
@app.on_event("startup")
async def startup_event():
    print("🎯 FastAPI startup event triggered")
    print(f"Database file exists: {os.path.exists('assignments.db')}")
    print(f"Environment PYTHON_PATH: {os.getenv('PYTHONPATH', 'Not set')}")
    
    # Test database connection
    try:
        conn = sqlite3.connect('assignments.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Database tables: {[table[0] for table in tables]}")
        conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    
    print("✅ Application startup completed successfully")

# A secret key is required for SessionMiddleware to sign the cookies.
SECRET_KEY = os.urandom(24)
# Set session expiry to 7 days (7 * 24 * 60 * 60 seconds)
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=SESSION_MAX_AGE)

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
        if 'access-control' in header_name.lower():
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
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173/home")  # Redirect to home page after login

# SQLite setup - use absolute path for production deployment
DB_PATH = os.getenv("DATABASE_PATH", "assignments.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# Drop old table if it exists
c.execute('DROP TABLE IF EXISTS assignments')

# Create new table with proper schema
c.execute('''
    CREATE TABLE IF NOT EXISTS question_assignments (
        id TEXT PRIMARY KEY,
        question TEXT NOT NULL,
        marks INTEGER NOT NULL,
        topic TEXT NOT NULL,
        evaluation_rubrics TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

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
        "version": "1.0.1"
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
        
        # Generate the redirect URI using FastAPI's request object
        redirect_uri = request.url_for('api_auth_google_callback')
        flow.redirect_uri = redirect_uri
        
        print(f"🔑 Redirect URI: {redirect_uri}")

        authorization_url, state = flow.authorization_url(
            access_type='offline', include_granted_scopes='true')
        
        request.session['state'] = state
        print(f"🔑 Auth URL generated successfully")
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
    state = request.session.get('state')
    if not state or state != request.query_params.get('state'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State mismatch")

    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
        flow.redirect_uri = request.url_for('api_auth_google_callback')

        authorization_response = str(request.url)
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        request.session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'login_timestamp': datetime.datetime.now().isoformat()  # Add login timestamp
        }
        
        return RedirectResponse(url=FRONTEND_URL)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': "An error occurred during token exchange", 'details': str(e)}
        )

@app.post("/api/auth/google/logout")
async def api_auth_google_logout(request: Request):
    """Logs the user out by clearing the session."""
    request.session.clear()
    return JSONResponse({'status': 'success', 'message': 'Logged out'})

@app.get("/api/check_auth")
async def api_check_auth(request: Request):
    """Checks if a user's session and credentials exist and haven't expired."""
    if 'credentials' in request.session:
        credentials_dict = request.session['credentials']
        
        # Check if login timestamp exists and if session has expired (7 days)
        if 'login_timestamp' in credentials_dict:
            login_time = datetime.datetime.fromisoformat(credentials_dict['login_timestamp'])
            current_time = datetime.datetime.now()
            time_diff = current_time - login_time
            
            # If more than 7 days have passed, clear session and return logged out
            if time_diff.days >= 7:
                request.session.clear()
                return JSONResponse({'logged_in': False, 'message': 'Session expired after 7 days'})
        
        return JSONResponse({'logged_in': True})
    return JSONResponse({'logged_in': False})

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

@app.get("/api/get-assignment-questions/{assignment_title}")
async def get_assignment_questions(assignment_title: str):
    """
    Get stored questions for an assignment based on the assignment title.
    This helps fetch evaluation criteria for grading.
    """
    try:
        # Extract topic from assignment title (format: "Assignment-{topic}")
        if assignment_title.startswith("Assignment-"):
            topic = assignment_title.replace("Assignment-", "")
            
            # Search for questions with matching topic
            c.execute('''
                SELECT id, question, marks, topic, evaluation_rubrics 
                FROM question_assignments 
                WHERE topic LIKE ?
                ORDER BY created_at DESC
            ''', (f'%{topic}%',))
            
            results = c.fetchall()
            
            questions = []
            for row in results:
                questions.append({
                    'id': row[0],
                    'question': row[1],
                    'marks': row[2],
                    'topic': json.loads(row[3]),
                    'rubrics': json.loads(row[4])
                })
            
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
    try:
        stored_questions = []
        
        for question_data in req.questions:
            # Generate unique ID using timestamp and UUID
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = f"{timestamp}_{str(uuid.uuid4())[:8]}"
            
            # Extract data from the question
            question_text = question_data.get("question", "")
            marks = question_data.get("marks", 0)
            topic = json.dumps(question_data.get("topic", []))  # Store as JSON string
            evaluation_rubrics = json.dumps(question_data.get("rubrics", []))  # Store as JSON string
            
            # Insert into database
            c.execute('''
                INSERT INTO question_assignments 
                (id, question, marks, topic, evaluation_rubrics, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (unique_id, question_text, marks, topic, evaluation_rubrics, datetime.datetime.now()))
            
            stored_questions.append({
                "id": unique_id,
                "question": question_text,
                "marks": marks,
                "topic": json.loads(topic),
                "rubrics": json.loads(evaluation_rubrics)
            })
        
        conn.commit()
        
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
    try:
        c.execute('''
            SELECT id, question, marks, topic, evaluation_rubrics, created_at 
            FROM question_assignments 
            ORDER BY created_at DESC
        ''')
        
        rows = c.fetchall()
        questions = []
        
        for row in rows:
            questions.append({
                "id": row[0],
                "question": row[1],
                "marks": row[2],
                "topic": json.loads(row[3]),
                "rubrics": json.loads(row[4]),
                "created_at": row[5]
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
