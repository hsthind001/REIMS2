# ⚡ REIMS2 Quick Start Commands

**Copy and paste these commands to get started fast!**

---

## 🚀 First Time Setup (One-Time Only)

### 1. Activate Docker Group
```bash
# Log out and log back in, OR run this:
newgrp docker
```

### 2. Test Docker Works
```bash
docker ps
# Should work WITHOUT asking for password
```

---

## 🎯 Start REIMS2 (Every Time You Use It)

### Simple Method (Recommended)
```bash
cd ~/Documents/GitHub/REIMS2
./start-reims.sh
```

### Manual Method
```bash
cd ~/Documents/GitHub/REIMS2
docker compose up -d
sleep 60  # Wait for services to start
docker compose ps
```

---

## 🌐 Access REIMS2

### Open in Browser
```
Frontend:       http://localhost:5173
API Docs:       http://localhost:8000/docs
Celery Monitor: http://localhost:5555
MinIO Console:  http://localhost:9001
```

### Login Credentials
```
Username: admin
Password: Admin123!
```

---

## ⚙️ Optimize System (Recommended - One Time)

### Run Optimization Script
```bash
cd ~/Documents/GitHub/REIMS2
./optimize-for-reims.sh
```

### Then Reboot
```bash
sudo reboot
```

---

## 🐭 Fix Mouse Stuttering (If Needed)

### Run Mouse Fix Script
```bash
cd ~/Documents/GitHub/REIMS2
./fix-mouse-stutter.sh
```

### Then Reboot
```bash
sudo reboot
```

---

## 📊 Check Status & Monitor

### Check Service Status
```bash
docker compose ps
```

### Check All Containers
```bash
docker ps
```

### Monitor Resources
```bash
docker stats
```

### View Logs (All Services)
```bash
docker compose logs -f
```

### View Specific Service Logs
```bash
docker logs reims-backend -f
docker logs reims-frontend -f
docker logs reims-celery-worker -f
docker logs reims-postgres -f
```

---

## 🔧 Common Operations

### Stop REIMS2
```bash
cd ~/Documents/GitHub/REIMS2
docker compose down
```

### Restart REIMS2
```bash
cd ~/Documents/GitHub/REIMS2
docker compose restart
```

### Restart Specific Service
```bash
docker compose restart backend
docker compose restart frontend
docker compose restart celery-worker
```

### Rebuild Service
```bash
docker compose up -d --build backend
```

---

## 🗄️ Database Operations

### Access PostgreSQL CLI
```bash
docker exec -it reims-postgres psql -U reims -d reims
```

### Run SQL Query
```bash
docker exec reims-postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM properties;"
```

### Run Migrations
```bash
docker exec reims-backend alembic upgrade head
```

### Backup Database
```bash
docker exec reims-postgres pg_dump -U reims reims > backup_$(date +%Y%m%d).sql
```

---

## 🔍 Health Checks

### Backend API Health
```bash
curl http://localhost:8000/api/v1/health
```

### Check PostgreSQL
```bash
docker exec reims-postgres pg_isready -U reims
```

### Check Redis
```bash
docker exec reims-redis redis-cli ping
```

---

## 📈 System Monitoring

### CPU & Memory
```bash
htop
```

### Disk I/O
```bash
sudo iotop
```

### Disk Usage
```bash
df -h
ncdu /
```

### Docker Disk Usage
```bash
docker system df
```

---

## 🧹 Cleanup

### Clean Docker System
```bash
docker system prune -f
```

### Clean Docker Volumes (⚠️ Destroys Data!)
```bash
docker volume prune
```

### Full Docker Cleanup (⚠️ Destroys Everything!)
```bash
docker system prune -a --volumes
```

---

## 🔄 Update System

### Update Ubuntu Packages
```bash
sudo apt update && sudo apt upgrade -y
```

### Update Docker Images
```bash
cd ~/Documents/GitHub/REIMS2
docker compose pull
docker compose up -d
```

---

## 🎮 GPU Operations (If NVIDIA Drivers Installed)

### Check NVIDIA GPU
```bash
nvidia-smi
```

### Install NVIDIA Drivers
```bash
sudo ubuntu-drivers autoinstall
sudo reboot
```

---

## ⚡ Performance Testing

### PostgreSQL Benchmark
```bash
docker exec reims-postgres pgbench -i -s 50 reims
docker exec reims-postgres pgbench -c 10 -j 2 -t 10000 reims
```

### Redis Benchmark
```bash
docker exec reims-redis redis-benchmark -q -n 100000
```

### Disk Speed Test
```bash
sudo hdparm -Tt /dev/nvme0n1
```

---

## 🛠️ Troubleshooting

### Fix Docker Permissions
```bash
sudo usermod -aG docker $USER
newgrp docker
# OR log out and log back in
```

### Check Port Usage
```bash
sudo lsof -i :5173  # Frontend
sudo lsof -i :8000  # Backend
sudo lsof -i :5433  # PostgreSQL
```

### Kill Process on Port
```bash
sudo kill -9 $(sudo lsof -t -i:5173)
```

### Reset Docker
```bash
docker compose down -v
docker system prune -a
docker compose up -d
```

---

## 📝 Useful Aliases (Add to ~/.bashrc)

### Edit .bashrc
```bash
nano ~/.bashrc
```

### Add These Lines
```bash
# REIMS2 Aliases
alias reims-start='cd ~/Documents/GitHub/REIMS2 && ./start-reims.sh'
alias reims-stop='cd ~/Documents/GitHub/REIMS2 && docker compose down'
alias reims-restart='cd ~/Documents/GitHub/REIMS2 && docker compose restart'
alias reims-logs='cd ~/Documents/GitHub/REIMS2 && docker compose logs -f'
alias reims-status='cd ~/Documents/GitHub/REIMS2 && docker compose ps'
alias reims-stats='docker stats'
alias reims-cd='cd ~/Documents/GitHub/REIMS2'
alias reims-backend='docker logs reims-backend -f'
alias reims-frontend='docker logs reims-frontend -f'
alias reims-celery='docker logs reims-celery-worker -f'
alias reims-db='docker exec -it reims-postgres psql -U reims -d reims'
```

### Reload .bashrc
```bash
source ~/.bashrc
```

### Now You Can Use
```bash
reims-start       # Start REIMS2
reims-stop        # Stop REIMS2
reims-logs        # View all logs
reims-status      # Check status
reims-stats       # Monitor resources
reims-backend     # View backend logs
reims-db          # Access database
```

---

## 🎯 Complete Startup Sequence

### Copy-Paste This Entire Block

```bash
# Activate Docker (first time only)
newgrp docker

# Navigate to REIMS2
cd ~/Documents/GitHub/REIMS2

# Start all services
./start-reims.sh

# Wait a moment, then check status
sleep 5
docker compose ps

# Open in browser
echo "Open these URLs in your browser:"
echo "  Frontend:  http://localhost:5173"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Flower:    http://localhost:5555"
echo ""
echo "Login: admin / Admin123!"
```

---

## 🚀 Most Common Commands

### Daily Use
```bash
# Start REIMS2
cd ~/Documents/GitHub/REIMS2 && ./start-reims.sh

# Stop REIMS2
cd ~/Documents/GitHub/REIMS2 && docker compose down

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### Weekly Maintenance
```bash
# Update and clean
sudo apt update && sudo apt upgrade -y
docker system prune -f

# Backup database
cd ~/Documents/GitHub/REIMS2
docker exec reims-postgres pg_dump -U reims reims > backup_$(date +%Y%m%d).sql
```

---

## 📚 Documentation Links

- **[READY_TO_START.md](READY_TO_START.md)** - Complete getting started guide
- **[CHEAT_SHEET.md](CHEAT_SHEET.md)** - Comprehensive command reference
- **[LAPTOP_OPTIMIZATION_GUIDE.md](LAPTOP_OPTIMIZATION_GUIDE.md)** - Performance optimization
- **[SYSTEM_STATUS_SUMMARY.md](SYSTEM_STATUS_SUMMARY.md)** - Current system status
- **[MOUSE_FIX_GUIDE.md](MOUSE_FIX_GUIDE.md)** - Touchpad troubleshooting
- **[USER_GUIDE.md](USER_GUIDE.md)** - How to use REIMS2

---

**🎯 Start with this**: `cd ~/Documents/GitHub/REIMS2 && ./start-reims.sh` 🚀
