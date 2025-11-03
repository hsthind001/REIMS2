# Use the pre-built base image with all dependencies
FROM reims-base:latest

# Set working directory (already set in base, but explicit for clarity)
WORKDIR /app

# Copy application code (ONLY THIS LAYER CHANGES FREQUENTLY)
# All system deps and Python packages are already in base image
COPY . .

# Create directory for temp files
RUN mkdir -p /tmp

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

