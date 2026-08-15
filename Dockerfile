FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing bytecode and enable bufferless logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install essential system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY . .

# Expose FastAPI backend (8000) and Streamlit UI (8501)
EXPOSE 8000
EXPOSE 8501

# Default startup command: Train model artifacts and serve FastAPI backend
CMD ["sh", "-c", "python -m src.train && uvicorn src.api:app --host 0.0.0.0 --port 8000"]
