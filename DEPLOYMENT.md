# Deployment Guide

## Environment Variables Required for Production

### Backend (.env file)
```
# Google API Configuration
GOOGLE_API_KEY=your-google-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here

# Application Configuration
ALLOWED_ORIGINS=https://your-frontend-domain.com
FRONTEND_URL=https://your-frontend-domain.com/home
DATABASE_PATH=/app/data/assignments.db
CLIENT_SECRETS_FILE=/app/config/client_secret.json
```

### Frontend Environment Variables
```
NODE_ENV=production
```

## Google OAuth Configuration for Production

1. **Update Google Cloud Console**:
   - Go to Google Cloud Console → APIs & Services → Credentials
   - Edit your OAuth 2.0 client
   - Add production domains to:
     - **Authorized JavaScript origins**: `https://your-frontend-domain.com`
     - **Authorized redirect URIs**: `https://your-backend-domain.com/api/auth/google/callback`

2. **Update client_secret.json** for production:
   ```json
   {
     "web": {
       "redirect_uris": ["https://your-backend-domain.com/api/auth/google/callback"],
       "javascript_origins": ["https://your-frontend-domain.com"]
     }
   }
   ```

## Platform-Specific Deployment Notes

### Render.com
1. Set environment variables in Render dashboard
2. Upload `client_secret.json` as a secret file
3. Ensure database persistence with Render Disks

### Vercel (Frontend)
1. Set `NODE_ENV=production` in environment variables
2. Update `config.js` with production backend URL

### Railway
1. Set environment variables in Railway dashboard
2. Configure volume mounts for database persistence

### Docker
1. Use `.env.template` as reference
2. Mount volumes for database and config files
3. Ensure proper file permissions

## Security Checklist

- [ ] All hardcoded URLs removed
- [ ] Environment variables configured
- [ ] Google OAuth domains updated
- [ ] API keys rotated (if previously exposed)
- [ ] Database file path configured for persistence
- [ ] CORS origins restricted to production domains
- [ ] Client secret file secured
