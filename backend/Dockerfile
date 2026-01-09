# Use official Python 3.11 slim image (better ML package compatibility)
FROM python:3.11-slim

# Install system dependencies including Rust toolchain and WeasyPrint dependencies
USER root
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    curl \
    build-essential \
    libpq-dev \
    pkg-config \
    libssl-dev \
    cmake \
    git \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    tesseract-ocr \
    poppler-utils \
    ghostscript \
    imagemagick \
    qpdf \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain (required for tokenizers and sentencepiece)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Upgrade pip, setuptools, and wheel for better package compatibility
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set working directory (already set in base, but explicit for clarity)
WORKDIR /app

# Copy entrypoint scripts first (rarely change, better caching)
# These are copied before app code to leverage Docker layer caching
COPY entrypoint.sh /entrypoint.sh
COPY celery-entrypoint.sh /celery-entrypoint.sh
COPY flower-entrypoint.sh /flower-entrypoint.sh
RUN chmod +x /entrypoint.sh /celery-entrypoint.sh /flower-entrypoint.sh

# Copy application code (ONLY THIS LAYER CHANGES FREQUENTLY)
# All system deps and Python packages are already in base image
# Copy in order: requirements first (if any), then app code
COPY . .

# Create directories for temp files and logs, set ownership
RUN mkdir -p /tmp /var/log/reims2 && chown -R appuser:appgroup /app /tmp /var/log/reims2

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Use entrypoint script for automatic database initialization
ENTRYPOINT ["/entrypoint.sh"]

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
