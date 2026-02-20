#!/usr/bin/env python3
"""
Backend startup script
Run this from the backend directory: python run.py
Or from root: python -m backend.run
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from backend.main import app
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
