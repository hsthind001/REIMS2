# Starting REIMS Services

This guide ensures services start reliably every time.

## Quick Start

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f backend
docker compose logs -f frontend
```

## Prerequisites

1. **Docker and Docker Compose** must be installed
2. **Base image must be built** (see below)

## First-Time Setup

### 1. Build the Base Image

The base image contains all Python dependencies. Rebuild it when `requirements.txt` changes:

```bash
cd backend
docker build -f Dockerfile.base -t reims-base:latest .
```

### 2. Build Application Images

```bash
cd ..
docker compose build
```

### 3. Start Services

```bash
docker compose up -d
```

## Troubleshooting

### Backend Won't Start

1. **Check logs:**
   ```bash
   docker logs reims-backend --tail 50
   ```

2. **Validate imports:**
   ```bash
   docker exec reims-backend python3 /app/scripts/validate_startup.py
   ```

3. **Rebuild base image** (if dependencies changed):
   ```bash
   cd backend
   docker build -f Dockerfile.base -t reims-base:latest .
   cd ..
   docker compose build backend
   docker compose up -d backend
   ```

### Frontend Can't Connect to Backend

1. **Check backend health:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

2. **Verify CORS settings** in `backend/app/core/config.py`

3. **Check network:**
   ```bash
   docker compose ps
   ```

### Services Keep Restarting

1. **Check for import errors:**
   ```bash
   docker logs reims-backend | grep -i "error\|traceback"
   ```

2. **Verify database connectivity:**
   ```bash
   docker exec reims-backend pg_isready -h postgres -p 5432 -U reims
   ```

3. **Check Redis:**
   ```bash
   docker exec reims-backend redis-cli -h redis ping
   ```

## Health Checks

- **Backend:** http://localhost:8000/api/v1/health
- **Frontend:** http://localhost:5173
- **PostgreSQL:** Port 5433 (mapped from 5432)
- **Redis:** Port 6379
- **MinIO Console:** http://localhost:9001

## Common Issues

### Missing Dependencies

If you see `ModuleNotFoundError`, rebuild the base image:

```bash
cd backend
docker build -f Dockerfile.base -t reims-base:latest .
cd ..
docker compose build backend
docker compose restart backend
```

### Permission Errors

If you see permission errors for `/var/log/reims2`:

```bash
docker exec -u root reims-backend mkdir -p /var/log/reims2
docker exec -u root reims-backend chown -R appuser:appgroup /var/log/reims2
docker compose restart backend
```

### Port Conflicts

If ports are already in use:

```bash
# Find what's using the port
sudo lsof -i :8000
sudo lsof -i :5173

# Stop conflicting services or change ports in docker-compose.yml
```

## Maintenance

### Update Dependencies

1. Edit `backend/requirements.txt`
2. Rebuild base image:
   ```bash
   cd backend
   docker build -f Dockerfile.base -t reims-base:latest .
   ```
3. Rebuild and restart:
   ```bash
   cd ..
   docker compose build backend
   docker compose restart backend
   ```

### Clean Restart

```bash
# Stop all services
docker compose down

# Remove volumes (WARNING: deletes data)
# docker compose down -v

# Rebuild and start
docker compose build
docker compose up -d
```

## Production Notes

- Set `SECRET_KEY` environment variable
- Disable `--reload` flag in production
- Use proper database backups
- Configure proper CORS origins
- Set up monitoring and logging

