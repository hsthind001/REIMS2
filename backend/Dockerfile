# Use the pre-built base image with all dependencies
FROM reims-base:latest

# Install PostgreSQL client for pg_isready and psql (for migrations and seeding)
# Install Redis tools for redis-cli (for Flower entrypoint script)
# Install curl for health checks
USER root
RUN apt-get update && apt-get install -y postgresql-client redis-tools curl && rm -rf /var/lib/apt/lists/*

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

