#!/usr/bin/env python3
"""
Railway-specific startup script for FastAPI application
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting FastAPI server on 0.0.0.0:{port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        access_log=True,
        log_level="info"
    )
