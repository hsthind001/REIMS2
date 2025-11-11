# Docker Compose - Complete Stack Orchestration

Docker Compose configuration for running the entire REIMS2 stack with a single command.

## 📦 What's Included

The `docker-compose.yml` orchestrates all services:

1. **PostgreSQL 17.6** - Database
2. **pgAdmin** - PostgreSQL GUI
3. **Redis Stack** - Cache, broker, and RedisInsight
4. **MinIO** - S3-compatible storage
5. **Backend (FastAPI)** - Python API
6. **Celery Worker** - Background task processor
7. **Flower** - Celery monitoring
8. **Frontend (React)** - Vite dev server

## 🚀 Quick Start

### First-Time Setup (Automatic Database Initialization)

```bash
cd /home/gurpyar/Documents/R/REIMS2

# Start all services - database will be automatically initialized!
docker compose up -d

# Watch initialization logs
docker compose logs -f backend

# You should see:
# ✅ PostgreSQL is ready!
# ✅ Migrations complete!
# ✅ Database seeded successfully!
# ✅ Starting FastAPI application...
```

**What happens automatically:**
1. ⏳ **Waits for PostgreSQL** to be ready
2. 🔄 **Runs 7 Alembic migrations** (Balance Sheet & Income Statement Template v1.0)
3. 🌱 **Seeds 300+ accounts** (200 Balance Sheet + 100 Income Statement)
4. 👥 **Seeds 30+ lenders** (CIBC, KeyBank, Wells Fargo, etc.)
5. 🎯 **Starts FastAPI application**

**Total time:** ~15-20 seconds for fresh deployment

### Start All Services

```bash
cd /home/gurpyar/Documents/R/REIMS2

# Start all services in detached mode
docker compose up -d

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f backend
```

### Stop All Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes data)
docker compose down -v
```

## 📋 Service Details

### PostgreSQL
- **Container**: reims-postgres
- **Init Container**: reims-db-init (runs migrations & seeding)
- **Port**: 5433 (external), 5432 (internal)
- **User**: reims
- **Password**: reims
- **Database**: reims
- **Volume**: postgres-data (persistent storage)
- **Tables**: 13+ tables with 19 migrations
- **Seeded Data**: 300+ chart of accounts, 30+ lenders
- **Persistence**: ✅ All schema, tables, and data persist across restarts
- **Documentation**: See [DATABASE_PERSISTENCE.md](DATABASE_PERSISTENCE.md)

### pgAdmin
- **Container**: reims-pgadmin
- **Port**: 5050
- **URL**: http://localhost:5050
- **Email**: admin@pgadmin.com
- **Password**: admin
- **Volume**: pgadmin-data

### Redis Stack
- **Container**: reims-redis
- **Port**: 6379 (Redis), 8001 (RedisInsight)
- **RedisInsight**: http://localhost:8001
- **Volume**: redis-data

### MinIO (S3-Compatible Storage)
- **Container**: reims-minio
- **Init Container**: reims-minio-init (auto-creates buckets)
- **Ports**: 9000 (API), 9001 (Console)
- **Console**: http://localhost:9001
- **Access Key**: minioadmin
- **Secret Key**: minioadmin
- **Bucket**: reims (auto-created on startup)
- **Volume**: minio-data (persistent storage)
- **Persistence**: ✅ All files and buckets persist across restarts
- **Documentation**: See [MINIO_PERSISTENCE.md](MINIO_PERSISTENCE.md)

### Backend (FastAPI)
- **Container**: reims-backend
- **Port**: 8000
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Auto-reload**: Enabled (development)

### Celery Worker
- **Container**: reims-celery-worker
- **Queue**: Processes background tasks
- **Logs**: `docker compose logs celery-worker`

### Flower (Celery Monitor)
- **Container**: reims-flower
- **Port**: 5555
- **URL**: http://localhost:5555

### Frontend (React)
- **Container**: reims-frontend
- **Port**: 5173
- **URL**: http://localhost:5173
- **Hot reload**: Enabled (development)

## 🔧 Common Commands

### Service Management

```bash
# Start all services
docker compose up -d

# Start specific service
docker compose up -d postgres

# Stop all services
docker compose down

# Restart a service
docker compose restart backend

# Rebuild and start
docker compose up -d --build

# Scale a service
docker compose up -d --scale celery-worker=3
```

### Logs & Monitoring

```bash
# View all logs
docker compose logs

# Follow logs (live)
docker compose logs -f

# View specific service logs
docker compose logs backend
docker compose logs postgres

# Last 100 lines
docker compose logs --tail=100
```

### Service Status

```bash
# List running services
docker compose ps

# Check service health
docker compose ps --all

# View resource usage
docker stats
```

### Execute Commands in Containers

```bash
# Access PostgreSQL
docker compose exec postgres psql -U reims -d reims

# Access Redis CLI
docker compose exec redis redis-cli

# Access backend shell
docker compose exec backend bash

# Run Python in backend
docker compose exec backend python

# Access MinIO console (mc)
docker compose exec minio bash
```

### Database Operations

```bash
# Create database backup
docker compose exec postgres pg_dump -U reims reims > backup.sql

# Restore database
docker compose exec -T postgres psql -U reims reims < backup.sql

# Access database directly
docker compose exec postgres psql -U reims -d reims
```

## 🔄 Development Workflow

### Initial Setup

```bash
cd /home/gurpyar/Documents/R/REIMS2

# 1. Build and start all services
docker compose up -d --build

# 2. Wait for services to be healthy
docker compose ps

# 3. Access the application
# - Frontend: http://localhost:5173
# - Backend: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Making Changes

#### Backend Changes
```bash
# Changes are auto-reloaded (volume mounted)
# Edit files in ./backend/app/
# Server will restart automatically

# If you change requirements.txt:
docker compose build backend
docker compose up -d backend
```

#### Frontend Changes
```bash
# Changes are auto-reloaded (volume mounted)
# Edit files in ./src/
# Vite will hot-reload automatically

# If you change package.json:
docker compose build frontend
docker compose up -d frontend
```

### Debugging

```bash
# View backend logs
docker compose logs -f backend

# View all service logs
docker compose logs -f

# Access backend shell for debugging
docker compose exec backend bash

# Run commands in backend
docker compose exec backend python -c "from app.main import app; print('OK')"
```

## 🌐 Networking

All services are connected via `reims-network` bridge network.

**Service DNS Names (internal):**
- postgres
- redis
- minio
- backend
- frontend

**Example connection from backend to postgres:**
```python
DATABASE_URL = "postgresql://reims:reims@postgres:5432/reims"
```

## 💾 Data Persistence

All data is stored in Docker volumes:

| Volume | Service | Purpose |
|--------|---------|---------|
| postgres-data | PostgreSQL | Database files |
| pgadmin-data | pgAdmin | Configuration |
| redis-data | Redis | Cache & queue data |
| minio-data | MinIO | Uploaded files |

**List volumes:**
```bash
docker volume ls | grep reims
```

**Inspect volume:**
```bash
docker volume inspect postgres-data
```

**Backup volume:**
```bash
docker run --rm -v postgres-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz /data
```

## 🔒 Environment Variables

### Backend Configuration

All services use environment variables defined in `docker-compose.yml`.

**To override:**
1. Create `.env` file in project root
2. Add variables:
```env
POSTGRES_PASSWORD=your_secure_password
MINIO_ROOT_USER=your_minio_user
```

3. Docker Compose will automatically use these

### Environment Files

- `./backend/.env` - Backend-specific config
- `./.env` - Project-wide config (optional)

## 📊 Service Dependencies

```
Frontend → Backend → PostgreSQL
                  → Redis
                  → MinIO
                  
Celery Worker → Backend
             → PostgreSQL  
             → Redis
             → MinIO

Flower → Celery Worker
      → Redis
```

## 🛠️ Troubleshooting

### Database Initialization Issues

#### Migrations Not Running

```bash
# Check backend logs for errors
docker compose logs backend | grep -i "migration\|error"

# Manually run migrations
docker compose exec backend alembic upgrade head

# Check migration status
docker compose exec backend alembic current
```

#### Database Not Seeding

```bash
# Check if accounts table exists
docker compose exec postgres psql -U reims -d reims -c "\dt chart_of_accounts"

# Check account count
docker compose exec postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM chart_of_accounts;"

# Manually run seed scripts
docker compose exec backend bash
cd scripts
PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U reims -d reims -f seed_balance_sheet_template_accounts.sql
```

#### Skip Automatic Initialization

If you want to skip automatic initialization temporarily:

```yaml
# In docker-compose.yml, set:
environment:
  RUN_MIGRATIONS: "false"
  SEED_DATABASE: "false"
```

Then rebuild and restart:
```bash
docker compose up -d --force-recreate backend
```

### Service Won't Start

```bash
# Check logs
docker compose logs SERVICE_NAME

# Check if port is already in use
sudo netstat -tlnp | grep PORT

# Force recreate
docker compose up -d --force-recreate SERVICE_NAME
```

### Database Connection Failed

```bash
# Check if PostgreSQL is healthy
docker compose ps postgres

# Check PostgreSQL logs
docker compose logs postgres

# Test connection
docker compose exec postgres psql -U reims -d reims -c "SELECT 1;"
```

### Backend Errors

```bash
# View backend logs
docker compose logs backend

# Check if dependencies are installed
docker compose exec backend pip list

# Rebuild backend
docker compose build backend
docker compose up -d backend
```

### Volume Issues

```bash
# Remove and recreate volumes
docker compose down -v
docker compose up -d

# ⚠️ This deletes all data!
```

## 🔄 Production Deployment

### Production docker-compose.override.yml

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      - DEBUG=false
  
  frontend:
    build:
      target: production
    command: npm run preview
  
  # Remove development tools
  flower:
    profiles:
      - monitoring
```

**Run production:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 📈 Scaling Services

```bash
# Scale Celery workers
docker compose up -d --scale celery-worker=3

# Scale backend
docker compose up -d --scale backend=2

# View scaled services
docker compose ps
```

## 🧹 Cleanup

### Remove Everything

```bash
# Stop and remove containers
docker compose down

# Remove volumes too (⚠️ deletes all data)
docker compose down -v

# Remove images
docker compose down --rmi all

# Complete cleanup
docker compose down -v --rmi all --remove-orphans
```

### Prune Docker System

```bash
# Remove unused containers
docker container prune

# Remove unused volumes
docker volume prune

# Remove unused images
docker image prune

# Remove everything unused
docker system prune -a --volumes
```

## 🔐 Security Best Practices

### For Production

1. **Change default passwords**
```yaml
environment:
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  MINIO_ROOT_USER: ${MINIO_ROOT_USER}
  MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
```

2. **Use secrets**
```yaml
secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
```

3. **Disable unnecessary ports**
```yaml
# Only expose what's needed
ports:
  - "127.0.0.1:5432:5432"  # Only localhost
```

4. **Use read-only volumes where possible**
```yaml
volumes:
  - ./config:/app/config:ro  # Read-only
```

## 📝 Useful Aliases

Add to your `.bashrc`:

```bash
# REIMS Docker Compose shortcuts
alias reims-up='cd /home/gurpyar/Documents/R/REIMS2 && docker compose up -d'
alias reims-down='cd /home/gurpyar/Documents/R/REIMS2 && docker compose down'
alias reims-logs='cd /home/gurpyar/Documents/R/REIMS2 && docker compose logs -f'
alias reims-ps='cd /home/gurpyar/Documents/R/REIMS2 && docker compose ps'
alias reims-restart='cd /home/gurpyar/Documents/R/REIMS2 && docker compose restart'
```

Then use:
```bash
reims-up      # Start everything
reims-logs    # View logs
reims-down    # Stop everything
```

## 🎯 Quick Reference

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start all services in background |
| `docker compose down` | Stop all services |
| `docker compose logs -f` | View live logs |
| `docker compose ps` | List running services |
| `docker compose restart SERVICE` | Restart a service |
| `docker compose build SERVICE` | Rebuild a service |
| `docker compose exec SERVICE bash` | Access service shell |

## 🌟 Advantages of Docker Compose

✅ **One Command Start** - `docker compose up -d`  
✅ **Automatic Networking** - Services can talk to each other  
✅ **Dependency Management** - Start services in correct order  
✅ **Volume Management** - Persistent data  
✅ **Environment Configuration** - Easy config management  
✅ **Service Discovery** - Use service names as hostnames  
✅ **Health Checks** - Wait for services to be ready  
✅ **Easy Scaling** - Scale services horizontally  

## 📞 Support

- Docker Compose Docs: https://docs.docker.com/compose/
- Compose File Reference: https://docs.docker.com/compose/compose-file/
- Best Practices: https://docs.docker.com/develop/dev-best-practices/

---

**Location**: `/home/gurpyar/Documents/R/REIMS2/`

Your complete stack is now fully containerized and ready for development or production deployment! 🎉

