#!/bin/bash

# Create necessary directories
mkdir -p /app/data /app/config

# Check if client_secret.json exists, if not create from environment variable
if [ ! -f "/app/config/client_secret.json" ] && [ ! -z "$CLIENT_SECRET_JSON" ]; then
    echo "$CLIENT_SECRET_JSON" > /app/config/client_secret.json
    echo "Created client_secret.json from environment variable"
fi

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
