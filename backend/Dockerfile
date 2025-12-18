FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements separately to cache dependencies
COPY requirements.txt .

# Install dependencies
# IMPORTANT: Install CPU-only torch first to avoid downloading huge GPU libs
# This saves ~700MB+ in image size
# RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port (Cloud Run/Render will set PORT env variable)
EXPOSE 8080

# Run command - use uvicorn directly for production
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
