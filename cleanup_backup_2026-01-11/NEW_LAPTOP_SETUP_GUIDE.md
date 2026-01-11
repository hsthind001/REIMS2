# REIMS2 Setup Guide - New Laptop

**Date**: January 3, 2026
**System**: Acer Predator PHN16-73
**OS**: Ubuntu 24.04.3 LTS
**Hardware**: Intel Core Ultra 9 275HX, 32GB RAM, 1TB SSD, RTX 5070

---

## Quick Setup (Automated)

### Option 1: Run the automated setup script

```bash
cd /home/hsthind/Documents/GitHub/REIMS2
./setup-new-laptop.sh
```

This script will:
- ✅ Update system packages
- ✅ Install Git and configure it
- ✅ Install Docker and Docker Compose
- ✅ Install Node.js 20.x LTS and npm
- ✅ Install development tools (build-essential, python3, etc.)
- ✅ Initialize Git repository
- ✅ Create .env configuration file
- ✅ Add your user to the docker group

**⚠️ IMPORTANT**: After running the script, you must log out and log back in for the docker group membership to take effect!

---

## Manual Setup (Step by Step)

If you prefer to install manually or the script fails:

### 1. Install Git

```bash
sudo apt update
sudo apt install -y git

# Configure git
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 2. Install Docker

```bash
# Remove old versions
sudo apt remove -y docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
```

**⚠️ Log out and log back in** after adding yourself to the docker group!

### 3. Install Node.js and npm

```bash
# Install Node.js 20.x LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version
npm --version
```

### 4. Initialize Git Repository

```bash
cd /home/hsthind/Documents/GitHub/REIMS2
git init

# Create initial commit (optional)
git add .
git commit -m "Initial commit - REIMS2 on new laptop"
```

### 5. Create Environment File

```bash
cd /home/hsthind/Documents/GitHub/REIMS2

# Copy example or create new .env file
cp .env.example .env

# Or use the provided template (see below)
```

---

## Environment Configuration

Create a [.env](.env) file in the project root with the following content:

```bash
# PostgreSQL Configuration
POSTGRES_USER=reims
POSTGRES_PASSWORD=reims
POSTGRES_DB=reims
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://reims:reims@postgres:5432/reims

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# MinIO Configuration
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET_NAME=reims-documents
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# API Configuration
API_V1_STR=/api/v1
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Frontend Configuration
VITE_API_URL=http://localhost:8000
```

---

## Starting REIMS2

### 1. Start Docker Services

```bash
cd /home/hsthind/Documents/GitHub/REIMS2
docker compose up -d
```

### 2. Check Service Status

```bash
# View all running containers
docker compose ps

# Check logs
docker compose logs -f

# Check specific service logs
docker logs reims-backend -f
docker logs reims-frontend -f
docker logs reims-celery-worker -f
```

### 3. Wait for Services to Initialize

Wait 30-60 seconds for all services to start. You should see:
- ✅ `reims-postgres` - Database
- ✅ `reims-redis` - Cache and queue
- ✅ `reims-minio` - Object storage
- ✅ `reims-backend` - FastAPI application
- ✅ `reims-celery-worker` - Background worker
- ✅ `reims-flower` - Celery monitoring
- ✅ `reims-frontend` - React application

### 4. Access the Application

Open your browser and navigate to:

- **Frontend**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs
- **Celery Monitor (Flower)**: http://localhost:5555
- **MinIO Console**: http://localhost:9001

### 5. Login

Default credentials:
- **Username**: `admin`
- **Password**: `Admin123!`

---

## Verification Checklist

Run these commands to verify everything is working:

```bash
# 1. Check Docker
docker --version
docker compose version

# 2. Check if you can run docker without sudo
docker ps

# If this fails, you need to log out and log back in!

# 3. Check Node.js
node --version
npm --version

# 4. Check Git
git --version

# 5. Check all containers are running
docker compose ps

# 6. Test backend API
curl http://localhost:8000/api/v1/health

# 7. Test frontend
curl http://localhost:5173

# 8. Check database connection
docker exec reims-postgres psql -U reims -d reims -c "SELECT 1"
```

---

## Common Issues and Solutions

### Issue: "Permission denied" when running docker commands

**Solution**: You need to log out and log back in after being added to the docker group.

```bash
# Check if you're in the docker group
groups

# If 'docker' is not listed, log out and log back in
# Or run: newgrp docker
```

### Issue: Port already in use (5432, 5173, 8000, etc.)

**Solution**: Check what's using the port and stop it:

```bash
# Find process using port 5432 (PostgreSQL)
sudo lsof -i :5432

# Kill the process if needed
sudo kill -9 <PID>

# Or change the port in docker-compose.yml
```

### Issue: Docker daemon not running

**Solution**: Start the Docker service:

```bash
sudo systemctl start docker
sudo systemctl enable docker
sudo systemctl status docker
```

### Issue: Services won't start

**Solution**: Check logs and restart:

```bash
# View all logs
docker compose logs

# Restart all services
docker compose down
docker compose up -d

# Check individual service logs
docker logs reims-backend -f
```

### Issue: Database migration errors

**Solution**: Run migrations manually:

```bash
# Check db-init logs
docker logs reims-db-init

# Run migrations manually
docker exec reims-backend alembic upgrade head
```

### Issue: Frontend not loading

**Solution**: Check frontend logs and rebuild:

```bash
# Check logs
docker logs reims-frontend -f

# Rebuild frontend
docker compose up -d --build frontend
```

---

## System Architecture

REIMS2 consists of 8 Docker services:

```
┌─────────────────────────────────────────────────┐
│                   REIMS2                        │
├─────────────────────────────────────────────────┤
│                                                 │
│  Frontend (React + Vite)                        │
│  ↓                                              │
│  Backend (FastAPI)                              │
│  ↓                                              │
│  ├── PostgreSQL (Database)                      │
│  ├── Redis (Cache + Queue)                      │
│  ├── MinIO (S3 Storage)                         │
│  ├── Celery Worker (PDF Processing)            │
│  └── Flower (Monitoring)                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5433 | Database (external port) |
| Redis | 6379 | Cache and message broker |
| MinIO | 9000, 9001 | Object storage, console |
| Backend | 8000 | FastAPI REST API |
| Flower | 5555 | Celery monitoring |
| Frontend | 5173 | React web application |

---

## Useful Commands

### Docker Management

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart a specific service
docker compose restart backend

# View logs
docker compose logs -f

# View specific service logs
docker logs reims-backend -f

# Rebuild a service
docker compose up -d --build backend

# Remove all containers and volumes (CAUTION: destroys data!)
docker compose down -v
```

### Database Operations

```bash
# Access PostgreSQL CLI
docker exec -it reims-postgres psql -U reims -d reims

# Run SQL query
docker exec reims-postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM properties;"

# Run migrations
docker exec reims-backend alembic upgrade head

# Create migration
docker exec reims-backend alembic revision --autogenerate -m "description"

# Backup database
docker exec reims-postgres pg_dump -U reims reims > backup.sql

# Restore database
cat backup.sql | docker exec -i reims-postgres psql -U reims -d reims
```

### Backend Operations

```bash
# Access backend shell
docker exec -it reims-backend bash

# Run Python shell
docker exec -it reims-backend python3

# Run tests
docker exec reims-backend python3 -m pytest /app/tests/ -v

# Check API health
curl http://localhost:8000/api/v1/health
```

### Frontend Operations

```bash
# Access frontend shell
docker exec -it reims-frontend sh

# View frontend logs
docker logs reims-frontend -f

# Rebuild frontend
docker compose up -d --build frontend
```

### Celery Operations

```bash
# View Celery worker logs
docker logs reims-celery-worker -f

# Restart Celery worker
docker compose restart celery-worker

# Monitor tasks in Flower
# Open: http://localhost:5555
```

---

## Next Steps

After setup is complete:

1. **Explore the System**: Read [START_HERE.md](START_HERE.md)
2. **User Guide**: Read [USER_GUIDE.md](USER_GUIDE.md)
3. **Test Upload**: Upload a test financial PDF
4. **Review Documentation**: See [README.md](README.md)
5. **Configure Git Remote** (if needed):
   ```bash
   git remote add origin <your-git-url>
   git branch -M main
   git push -u origin main
   ```

---

## Hardware Optimization Tips

Your Acer Predator has excellent specs. Here are some optimization tips:

### Docker Resource Allocation

Edit `/etc/docker/daemon.json` to allocate resources:

```json
{
  "default-runtime": "runc",
  "runtimes": {
    "nvidia": {
      "path": "/usr/bin/nvidia-container-runtime",
      "runtimeArgs": []
    }
  },
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

With 32GB RAM, you can comfortably run REIMS2 along with other applications.

### GPU Support (Optional)

If you want to use the RTX 5070 for OCR/AI tasks:

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

---

## Support and Documentation

- **Main Documentation**: [README.md](README.md)
- **Getting Started**: [GETTING_STARTED.md](GETTING_STARTED.md)
- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Quick Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **API Documentation**: http://localhost:8000/docs (when running)

---

## Summary

✅ **Installation**: Run `./setup-new-laptop.sh`
✅ **Important**: Log out and log back in after setup
✅ **Start Services**: `docker compose up -d`
✅ **Access**: http://localhost:5173
✅ **Login**: admin / Admin123!

**Your REIMS2 system is ready for use on your new laptop!** 🚀

---

**Questions or Issues?**

- Check the [troubleshooting section](#common-issues-and-solutions)
- Review Docker logs: `docker compose logs -f`
- Check service status: `docker compose ps`
