FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy start script
COPY start.sh .
RUN chmod +x start.sh

# Create necessary directories
RUN mkdir -p /app/data /app/config

# Expose port
EXPOSE $PORT

# Set environment variables
ENV PYTHONPATH=/app
ENV DATABASE_PATH=/app/data/assignments.db
ENV CLIENT_SECRETS_FILE=/app/config/client_secret.json

# Command to run the application
CMD ["./start.sh"]
