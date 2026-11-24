# Use official lightweight Python runtime as base image
FROM python:3.14-slim

# Prevent Python from writing .pyc files and enable unbuffered standard I/O
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HF_HOME=/app/model_cache

# Set working directory
WORKDIR /app

# Install system dependencies (build-essential for compiling C/C++ extensions, curl for HEALTHCHECK)
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency requirements
COPY requirements.txt .

# Upgrade pip and install CPU-optimized PyTorch first (reduces image size by ~3GB),
# followed by application dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download SentenceTransformer and CrossEncoder models into HF_HOME during image build
# so the container starts instantly without requiring runtime model downloads
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
    SentenceTransformer('all-MiniLM-L6-v2'); \
    CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# Copy application source code and frontend assets
COPY app/ ./app/
COPY frontend/ ./frontend/

# Create persistent storage directories for uploads and ChromaDB vector store
RUN mkdir -p /app/uploads /app/vectorstore /app/model_cache

# Expose the application port
EXPOSE 8000

# Health check to ensure the FastAPI server is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/ || exit 1

# Start FastAPI application using Uvicorn, respecting dynamic $PORT if provided by cloud platforms
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
