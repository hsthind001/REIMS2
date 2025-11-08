# Use the pre-built base image with all dependencies
FROM reims-base:latest

# Install PostgreSQL client for pg_isready and psql (for migrations and seeding)
# Install Redis tools for redis-cli (for Flower entrypoint script)
USER root
RUN apt-get update && apt-get install -y postgresql-client redis-tools && rm -rf /var/lib/apt/lists/*

# Set working directory (already set in base, but explicit for clarity)
WORKDIR /app

# Copy application code (ONLY THIS LAYER CHANGES FREQUENTLY)
# All system deps and Python packages are already in base image
COPY . .

# Copy and set entrypoint scripts
COPY entrypoint.sh /entrypoint.sh
COPY celery-entrypoint.sh /celery-entrypoint.sh
COPY flower-entrypoint.sh /flower-entrypoint.sh
RUN chmod +x /entrypoint.sh /celery-entrypoint.sh /flower-entrypoint.sh

# Create directory for temp files
RUN mkdir -p /tmp

# Expose port
EXPOSE 8000

# Use entrypoint script for automatic database initialization
ENTRYPOINT ["/entrypoint.sh"]

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

