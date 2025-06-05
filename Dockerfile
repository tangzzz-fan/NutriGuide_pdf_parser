# Multi-stage build for Python PDF Parser Service
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies for PDF parsing and OCR
RUN apt-get update && apt-get install -y \
    # Basic build tools
    gcc \
    g++ \
    curl \
    wget \
    # PDF processing dependencies
    libpoppler-cpp-dev \
    poppler-utils \
    # OCR dependencies
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    libtesseract-dev \
    # Image processing dependencies
    libopencv-dev \
    python3-opencv \
    # Additional image libraries
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    # Font support for better OCR
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app directory
WORKDIR /app

# Development stage
FROM base as development

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy source code
COPY . .

# Create directories with proper permissions
RUN mkdir -p /app/uploads /app/logs && \
    chmod 755 /app/uploads /app/logs

# Expose port
EXPOSE 8000

# Command for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-deps -r requirements.txt

# Copy source code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    mkdir -p /app/uploads /app/logs && \
    chown -R app:app /app && \
    chmod 755 /app/uploads /app/logs

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# Worker stage (for Celery workers)
FROM production as worker

# Switch back to root to modify startup
USER root

# Install additional monitoring tools for workers
RUN pip install flower

# Switch back to app user
USER app

# Default command for workers
CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info", "--concurrency=2"] 