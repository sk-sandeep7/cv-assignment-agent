#!/bin/bash

# Create necessary directories
mkdir -p /app/data /app/config

# Check if client_secret.json exists, if not create from environment variable
if [ ! -f "/app/config/client_secret.json" ]; then
    if [ ! -z "$CLIENT_SECRET_JSON" ]; then
        echo "$CLIENT_SECRET_JSON" > /app/config/client_secret.json
        echo "Created client_secret.json from CLIENT_SECRET_JSON environment variable"
    elif [ ! -z "$CLIENT_SECRET_BASE64" ]; then
        echo "$CLIENT_SECRET_BASE64" | base64 -d > /app/config/client_secret.json
        echo "Created client_secret.json from base64 encoded environment variable"
    elif [ ! -z "$GOOGLE_CLIENT_ID" ] && [ ! -z "$GOOGLE_CLIENT_SECRET" ]; then
        # Create client_secret.json from individual components
        cat > /app/config/client_secret.json << EOF
{
  "web": {
    "client_id": "$GOOGLE_CLIENT_ID",
    "project_id": "${GOOGLE_PROJECT_ID:-classroom-project-470618}",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "$GOOGLE_CLIENT_SECRET",
    "redirect_uris": ["https://${RAILWAY_PUBLIC_DOMAIN}/api/auth/google/callback"],
    "javascript_origins": ["https://${RAILWAY_PUBLIC_DOMAIN}"]
  }
}
EOF
        echo "Created client_secret.json from individual environment variables"
    else
        echo "Warning: No client secret configuration found. Please set CLIENT_SECRET_JSON or GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET"
    fi
fi

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
