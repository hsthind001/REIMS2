# REIMS2 Command Cheat Sheet

Quick reference for common REIMS2 operations.

---

## 🚀 Quick Start

```bash
# 1. Setup (one-time)
cd /home/hsthind/Documents/GitHub/REIMS2
./setup-new-laptop.sh

# 2. Log out and log back in (required!)

# 3. Start REIMS2
docker compose up -d

# 4. Access the application
# Open browser: http://localhost:5173
# Login: admin / Admin123!
```

---

## 🐳 Docker Commands

### Start/Stop Services

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes all data!)
docker compose down -v

# Restart all services
docker compose restart

# Restart specific service
docker compose restart backend
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker logs reims-backend -f
docker logs reims-frontend -f
docker logs reims-celery-worker -f
docker logs reims-postgres -f
docker logs reims-redis -f
```

### Check Status

```bash
# List all containers
docker compose ps

# Check container health
docker ps

# View resource usage
docker stats
```

### Rebuild Services

```bash
# Rebuild and restart all services
docker compose up -d --build

# Rebuild specific service
docker compose up -d --build backend
docker compose up -d --build frontend
```

---

## 💾 Database Commands

### Access Database

```bash
# PostgreSQL CLI
docker exec -it reims-postgres psql -U reims -d reims

# Run SQL query from command line
docker exec reims-postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM properties;"
```

### Common Queries

```bash
# Count properties
docker exec reims-postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM properties;"

# List all tables
docker exec reims-postgres psql -U reims -d reims -c "\dt"

# Check chart of accounts count
docker exec reims-postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM chart_of_accounts;"

# View recent uploads
docker exec reims-postgres psql -U reims -d reims -c "SELECT id, property_id, statement_type, status FROM document_uploads ORDER BY upload_date DESC LIMIT 5;"

# Check financial data
docker exec reims-postgres psql -U reims -d reims -c "SELECT statement_type, COUNT(*) FROM financial_data GROUP BY statement_type;"
```

### Migrations

```bash
# Run migrations
docker exec reims-backend alembic upgrade head

# Create new migration
docker exec reims-backend alembic revision --autogenerate -m "description"

# Check migration history
docker exec reims-backend alembic history

# Downgrade one version
docker exec reims-backend alembic downgrade -1
```

### Backup/Restore

```bash
# Backup database
docker exec reims-postgres pg_dump -U reims reims > backup_$(date +%Y%m%d).sql

# Restore database
cat backup.sql | docker exec -i reims-postgres psql -U reims -d reims

# Backup to compressed file
docker exec reims-postgres pg_dump -U reims reims | gzip > backup_$(date +%Y%m%d).sql.gz
```

---

## 🔧 Backend Commands

### Access Backend

```bash
# Bash shell
docker exec -it reims-backend bash

# Python shell
docker exec -it reims-backend python3

# Interactive Python with app context
docker exec -it reims-backend python3 -c "from app.db.session import SessionLocal; db = SessionLocal(); print('Database connected')"
```

### Run Tests

```bash
# All tests
docker exec reims-backend python3 -m pytest /app/tests/ -v

# Specific test file
docker exec reims-backend python3 -m pytest /app/tests/test_models.py -v

# With coverage
docker exec reims-backend python3 -m pytest /app/tests/ --cov=/app --cov-report=html

# Specific test
docker exec reims-backend python3 -m pytest /app/tests/test_models.py::test_property_creation -v
```

### API Health Check

```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Pretty print JSON
curl -s http://localhost:8000/api/v1/health | jq

# Check API documentation
curl http://localhost:8000/docs
```

---

## 🎨 Frontend Commands

### Access Frontend

```bash
# Shell access
docker exec -it reims-frontend sh

# View logs
docker logs reims-frontend -f

# Rebuild frontend
docker compose up -d --build frontend
```

### Development

```bash
# Frontend auto-reloads when you edit files in src/
# Just save your changes and refresh the browser

# Check frontend build
docker exec reims-frontend npm run build

# Run linter
docker exec reims-frontend npm run lint
```

---

## ⚙️ Celery Commands

### Monitor Celery

```bash
# View worker logs
docker logs reims-celery-worker -f

# Restart worker
docker compose restart celery-worker

# Access Flower (Celery monitoring UI)
# Open: http://localhost:5555
```

### Celery Shell

```bash
# Access Celery shell
docker exec -it reims-celery-worker bash

# Inspect active tasks
docker exec reims-celery-worker celery -A app.celery_app inspect active

# Inspect registered tasks
docker exec reims-celery-worker celery -A app.celery_app inspect registered
```

---

## 📦 MinIO Commands

### Access MinIO

```bash
# MinIO Console
# Open: http://localhost:9001
# Login: minioadmin / minioadmin

# MinIO API endpoint
# http://localhost:9000
```

### MinIO CLI (mc)

```bash
# Install mc (MinIO Client)
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Configure mc
mc alias set reims http://localhost:9000 minioadmin minioadmin

# List buckets
mc ls reims

# List files in bucket
mc ls reims/reims-documents

# Copy file to MinIO
mc cp myfile.pdf reims/reims-documents/

# Download file from MinIO
mc cp reims/reims-documents/myfile.pdf ./
```

---

## 🔍 Troubleshooting Commands

### Check System Resources

```bash
# Docker resource usage
docker stats

# Disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

### Check Port Usage

```bash
# Check if port is in use
sudo lsof -i :5173  # Frontend
sudo lsof -i :8000  # Backend
sudo lsof -i :5433  # PostgreSQL
sudo lsof -i :6379  # Redis
sudo lsof -i :9000  # MinIO

# Kill process using port
sudo kill -9 <PID>
```

### Debug Container Issues

```bash
# Inspect container
docker inspect reims-backend

# Check container logs
docker logs reims-backend --tail 100

# Check container processes
docker top reims-backend

# Execute command in container
docker exec reims-backend ls -la /app
```

### Network Issues

```bash
# List Docker networks
docker network ls

# Inspect network
docker network inspect reims2_default

# Test connectivity between containers
docker exec reims-backend ping postgres
docker exec reims-backend ping redis
```

---

## 📊 Monitoring Commands

### Check Service Health

```bash
# All containers
docker compose ps

# Specific service health
curl http://localhost:8000/api/v1/health

# Database connection
docker exec reims-postgres pg_isready -U reims

# Redis connection
docker exec reims-redis redis-cli ping
```

### View Metrics

```bash
# Container stats
docker stats --no-stream

# Database size
docker exec reims-postgres psql -U reims -d reims -c "SELECT pg_size_pretty(pg_database_size('reims'));"

# Table sizes
docker exec reims-postgres psql -U reims -d reims -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

---

## 🛠️ Development Commands

### Git Operations

```bash
# Initialize repository
git init

# Add remote
git remote add origin <your-repo-url>

# Check status
git status

# Add all changes
git add .

# Commit changes
git commit -m "Your message"

# Push to remote
git push -u origin main

# Pull latest changes
git pull origin main
```

### Environment Management

```bash
# Edit environment variables
nano .env

# Restart services after .env changes
docker compose down
docker compose up -d
```

---

## 📱 Application URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | admin / Admin123! |
| API Docs | http://localhost:8000/docs | - |
| Flower | http://localhost:5555 | - |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |

---

## 🆘 Emergency Commands

### Complete Reset (⚠️ Destroys all data!)

```bash
# Stop and remove everything
docker compose down -v

# Remove all Docker resources
docker system prune -a --volumes

# Restart from scratch
docker compose up -d
```

### Backup Before Reset

```bash
# Backup database
docker exec reims-postgres pg_dump -U reims reims > backup_emergency_$(date +%Y%m%d_%H%M%S).sql

# Backup MinIO data (requires mc)
mc mirror reims/reims-documents ./minio_backup/

# Stop services
docker compose down -v

# Restart
docker compose up -d

# Restore database
cat backup_emergency_*.sql | docker exec -i reims-postgres psql -U reims -d reims
```

---

## 📖 Useful SQL Queries

```sql
-- View all properties
SELECT * FROM properties;

-- Count uploads by status
SELECT status, COUNT(*) FROM document_uploads GROUP BY status;

-- View recent extractions
SELECT id, upload_id, status, confidence_score, created_at
FROM extraction_logs
ORDER BY created_at DESC LIMIT 10;

-- Check financial data summary
SELECT statement_type, COUNT(*), SUM(amount)
FROM financial_data
GROUP BY statement_type;

-- View validation results
SELECT validation_status, COUNT(*)
FROM validation_results
GROUP BY validation_status;

-- Check user accounts
SELECT username, email, is_active, created_at FROM users;
```

---

## 💡 Pro Tips

### Faster Development

```bash
# Use aliases in ~/.bashrc
alias dc='docker compose'
alias dps='docker compose ps'
alias dlogs='docker compose logs -f'
alias dback='docker logs reims-backend -f'
alias dfront='docker logs reims-frontend -f'
alias dcelery='docker logs reims-celery-worker -f'
alias dpsql='docker exec -it reims-postgres psql -U reims -d reims'

# Then use:
dc up -d
dlogs
dback
```

### Watch Logs in Real-Time

```bash
# Multiple services in split terminal
# Terminal 1: Backend logs
docker logs reims-backend -f

# Terminal 2: Celery logs
docker logs reims-celery-worker -f

# Terminal 3: Frontend logs
docker logs reims-frontend -f
```

### Quick Database Queries

```bash
# Create a script: db-query.sh
#!/bin/bash
docker exec reims-postgres psql -U reims -d reims -c "$1"

# Usage:
./db-query.sh "SELECT COUNT(*) FROM properties;"
```

---

**Keep this cheat sheet handy for quick reference!** 🚀
