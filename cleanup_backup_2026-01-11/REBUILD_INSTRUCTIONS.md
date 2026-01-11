# Rebuilding Docker Images

## Why Rebuild?

Rebuild when:
- `requirements.txt` changes
- System dependencies change
- Base image needs updates
- After pulling new code with dependency changes

## Quick Fix (No Rebuild Needed)

If services are running but you need to fix dependencies:

```bash
./scripts/fix_backend_dependencies.sh
```

## Full Rebuild (Takes 10-30 minutes)

### Option 1: Rebuild Base Image Only (Recommended)

This rebuilds the base image with all Python dependencies. This is the slowest step but only needs to be done when dependencies change.

```bash
cd backend

# This will take 10-30 minutes depending on your system
docker build -f Dockerfile.base -t reims-base:latest .

cd ..
docker compose build backend
docker compose up -d backend
```

### Option 2: Rebuild Everything

```bash
docker compose build --no-cache
docker compose up -d
```

## Why Builds Take So Long

The base image installs many heavy dependencies:
- PyTorch (~2GB)
- Transformers
- OpenCV
- NumPy, Pandas, SciPy
- Many other ML/AI libraries

**Tip:** Builds are cached, so subsequent builds are faster unless you change `requirements.txt`.

## Current Working Setup

The current running containers work because:
1. The base image was built previously with dependencies
2. Code is mounted as volumes (changes apply immediately)
3. Missing dependencies can be installed in running containers

## When to Use Each Approach

**Use Quick Fix (`fix_backend_dependencies.sh`):**
- Adding a single missing package
- Fixing permission issues
- Services are already running

**Use Full Rebuild:**
- Major dependency updates
- Starting fresh
- After pulling code with dependency changes
- When quick fixes don't work

## Monitoring Build Progress

```bash
# In another terminal, watch the build
docker build -f Dockerfile.base -t reims-base:latest . 2>&1 | tee build.log

# Or build in background
nohup docker build -f Dockerfile.base -t reims-base:latest . > build.log 2>&1 &
tail -f build.log
```

## Troubleshooting Build Failures

### Dependency Conflicts

If you see dependency conflicts:
1. Check `requirements.txt` for version conflicts
2. Some packages may need to be commented out (like langchain with numpy 2.x)
3. Use the working container's versions as reference:
   ```bash
   docker exec reims-backend pip list > working_versions.txt
   ```

### Out of Memory

If build fails due to memory:
```bash
# Increase Docker memory limit in Docker Desktop settings
# Or build on a machine with more RAM
```

### Network Issues

If downloads fail:
```bash
# Retry the build
# Or use a different network/mirror
```

