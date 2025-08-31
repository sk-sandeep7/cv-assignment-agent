# Deployment Guide

## Railway Deployment (Recommended)

### Step 1: Prepare Your Repository
1. Ensure all changes are committed and pushed to GitHub
2. Make sure `railway.toml` and `Dockerfile` are in the root directory

### Step 2: Railway Setup
1. Visit [Railway.app](https://railway.app)
2. Sign up/Login with your GitHub account
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your `cv-assignment-agent` repository
5. Railway will automatically detect the Dockerfile

### Step 3: Environment Variables
Set these environment variables in Railway dashboard:

```
GOOGLE_API_KEY=your-google-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
ALLOWED_ORIGINS=https://your-frontend-domain.com
FRONTEND_URL=https://your-frontend-domain.com/home
DATABASE_PATH=/app/data/assignments.db
CLIENT_SECRETS_FILE=/app/config/client_secret.json
```

### Step 4: Upload client_secret.json
1. In Railway dashboard, go to your service
2. Click on "Settings" → "Variables"
3. Upload your `client_secret.json` file as a secret
4. Or manually create the JSON content as an environment variable

### Step 5: Configure Domain & HTTPS
1. Railway provides a custom domain automatically
2. Update your Google OAuth settings with the new domain:
   - **Authorized JavaScript origins**: `https://your-railway-domain.up.railway.app`
   - **Authorized redirect URIs**: `https://your-railway-domain.up.railway.app/api/auth/google/callback`

### Step 6: Update Frontend Configuration
Update your frontend's `config.js`:
```javascript
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://your-railway-domain.up.railway.app'  // Your Railway backend URL
  : 'http://localhost:8000';
```

## Manual Railway CLI Deployment

### Prerequisites
```bash
npm install -g @railway/cli
railway login
```

### Deploy Commands
```bash
# Initialize Railway project
railway login
railway link

# Set environment variables
railway variables set GOOGLE_API_KEY=your-key-here
railway variables set AZURE_OPENAI_ENDPOINT=your-endpoint
# ... (set all other variables)

# Deploy
railway up
```
