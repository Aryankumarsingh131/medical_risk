FROM python:3.11-slim

WORKDIR /app

# Install system libraries needed by XGBoost / OpenMP
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and models
COPY api/ ./api/
COPY src/ ./src/
COPY models/ ./models/

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
