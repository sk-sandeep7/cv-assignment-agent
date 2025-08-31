# Railway Deployment Checklist

## Pre-Deployment Steps
- [ ] All code committed and pushed to GitHub
- [ ] Environment variables documented in `.env.template`
- [ ] `requirements.txt` updated with all dependencies
- [ ] `railway.toml` and `Dockerfile` created
- [ ] Google OAuth client secrets ready

## Railway Deployment Steps
1. [ ] Create Railway account and connect GitHub
2. [ ] Deploy from GitHub repository
3. [ ] Set all environment variables in Railway dashboard
4. [ ] Upload or configure `client_secret.json`
5. [ ] Note the Railway-provided domain URL
6. [ ] Update Google OAuth settings with Railway domain
7. [ ] Update frontend configuration with Railway backend URL
8. [ ] Test the deployment

## Environment Variables to Set in Railway
```
GOOGLE_API_KEY=your-google-api-key
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
ALLOWED_ORIGINS=https://your-frontend-domain.com
FRONTEND_URL=https://your-frontend-domain.com/home
DATABASE_PATH=/app/data/assignments.db
CLIENT_SECRETS_FILE=/app/config/client_secret.json
```

## Optional: Client Secret as Environment Variable
Instead of uploading the file, you can set:
```
CLIENT_SECRET_JSON={"web":{"client_id":"...","client_secret":"...","redirect_uris":["..."]}}
```

## Post-Deployment
- [ ] Test authentication flow
- [ ] Test assignment creation
- [ ] Test grading functionality
- [ ] Verify database persistence
- [ ] Check logs for any errors
