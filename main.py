"""
Main Server Entry Point for Electricity Theft & Anomaly Detection System.

Runs the production FastAPI REST API server using uvicorn.

Usage:
    python main.py
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import uvicorn
from src.api import app
from src.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
