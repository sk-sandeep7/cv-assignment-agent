# Google Classroom Integration Setup

## Prerequisites

1. **Google Cloud Project**: You need a Google Cloud Project with the Google Classroom API enabled.
2. **OAuth 2.0 Credentials**: You need to create OAuth 2.0 credentials for a web application.

## Setting up Google OAuth Credentials

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note down your Project ID

### Step 2: Enable Google Classroom API

1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google Classroom API"
3. Click on it and press "Enable"

### Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Web application" as the application type
4. Add these Authorized Redirect URIs:
   ```
   http://localhost:8000/api/auth/google/callback
   ```
5. Add these Authorized JavaScript origins:
   ```
   http://localhost:5173
   http://localhost:8000
   ```

### Step 4: Download and Configure Credentials

1. After creating the credentials, click the download button to download the JSON file
2. Rename the downloaded file to `client_secret.json`
3. Place it in the `backend/` directory
4. The file should look like this:
   ```json
   {
     "web": {
       "client_id": "your-client-id.apps.googleusercontent.com",
       "project_id": "your-project-id",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
       "client_secret": "your-client-secret",
       "redirect_uris": ["http://localhost:8000/api/auth/google/callback"]
     }
   }
   ```

### Step 5: Test Your Setup

1. Replace the placeholder values in `backend/client_secret.json` with your actual credentials
2. Start the backend server: `cd backend && uvicorn main:app --reload`
3. Start the frontend: `cd gc-agent && npm run dev`
4. Go to `http://localhost:5173` and try to log in with Google

## OAuth Consent Screen

You may need to configure the OAuth consent screen:

1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" (for testing with any Google account) or "Internal" (if you have a Google Workspace)
3. Fill in the required information:
   - App name: "GC Agent"
   - User support email: Your email
   - App logo: Optional
   - App domain: `http://localhost:5173`
   - Developer contact information: Your email
4. Add scopes:
   - `https://www.googleapis.com/auth/classroom.courses.readonly`
   - `https://www.googleapis.com/auth/classroom.coursework.students`
5. Add test users if using external user type (you can add your own email)

## Features

After successful setup, users can:

1. **Login with Google**: Authenticate using their Google account
2. **Generate Questions**: Create AI-powered questions with evaluation rubrics
3. **View Google Classrooms**: See all their Google Classroom courses
4. **Create Assignments**: Post assignments directly to Google Classroom with:
   - Custom title format: "Assignment-[topic]"
   - Questions with marks in the description
   - Deadline selection
   - No evaluation rubrics in the description (stored separately)

## Security Notes

- The `client_secret.json` file contains sensitive information. Do not commit it to version control.
- For production deployment, use environment variables instead of the JSON file.
- The current setup allows OAuth over HTTP for local development only.

## Troubleshooting

1. **"redirect_uri_mismatch" error**: Make sure the redirect URI in your Google Cloud Console exactly matches `http://localhost:8000/api/auth/google/callback`

2. **"invalid_client" error**: Check that your `client_secret.json` file is properly formatted and contains the correct credentials

3. **"access_denied" error**: Make sure you've added the necessary scopes and the user has access to Google Classroom

4. **No courses showing**: Ensure the authenticated user is enrolled in or teaches Google Classroom courses
