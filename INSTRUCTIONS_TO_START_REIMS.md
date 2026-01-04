# How to Fix Docker and Start REIMS Backend

## Quick Start (Copy and Paste This)

Open your terminal and run this single command:

```bash
cd ~/Documents/GitHub/REIMS2 && ./fix-docker-and-start-reims.sh
```

When prompted, enter your sudo password.

That's it! The script will:
1. Fix the Docker configuration
2. Restart Docker
3. Start all REIMS services
4. Show you the access URLs

---

## What the Script Does

The script `fix-docker-and-start-reims.sh` will:

1. **Fix Docker Configuration**
   - Backs up `/etc/docker/daemon.json`
   - Fixes the broken `overlay2.override_kernel_check` setting

2. **Restart Services**
   - Stops Docker Desktop (if running)
   - Restarts system Docker with fixed config

3. **Start REIMS**
   - Stops any old containers
   - Starts all 8 REIMS services
   - Waits for initialization (90 seconds)

4. **Shows Status**
   - Service health checks
   - Access URLs
   - Login credentials

---

## Expected Output

You should see:
- ✓ Configuration fixed
- ✓ Docker is ready!
- ✓ Services starting up
- Access URLs at the end

---

## Access URLs (After Startup)

- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs
- **Celery Monitor:** http://localhost:5555
- **MinIO Console:** http://localhost:9001

**Login:** admin / Admin123!

---

## If You Get Errors

If the script fails, you can manually run these commands:

### Step 1: Fix Docker Config
```bash
# Create the fixed configuration
cat > /tmp/daemon.json.fixed << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-address-pools": [
    {
      "base": "172.80.0.0/16",
      "size": 24
    }
  ],
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check"
  ],
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  },
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 10
}
EOF

# Backup and apply fix
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup
sudo cp /tmp/daemon.json.fixed /etc/docker/daemon.json
```

### Step 2: Restart Docker
```bash
sudo systemctl restart docker
docker context use default
```

### Step 3: Start REIMS
```bash
cd ~/Documents/GitHub/REIMS2
docker compose up -d
```

### Step 4: Wait and Check
```bash
# Wait 90 seconds, then:
docker compose ps
```

---

## Troubleshooting

### Check if Docker is running:
```bash
docker ps
```

### View REIMS logs:
```bash
docker compose logs -f backend
```

### Restart REIMS services:
```bash
docker compose restart
```

### Stop everything:
```bash
docker compose down
```

---

## Summary

**The Problem:** Docker daemon config had invalid syntax
**The Fix:** Changed `"overlay2.override_kernel_check=true"` to `"overlay2.override_kernel_check"`
**The Result:** Docker runs successfully, REIMS services start normally

Your backend code is healthy - it just needed Docker to be running!
