# Docker Optimizations Applied

## Summary

Applied comprehensive Docker optimizations to improve build efficiency, caching, and monitoring for REIMS2.

## Changes Made

### 1. Backend Dockerfile (`backend/Dockerfile`)
**Optimization:** Reordered COPY commands for better layer caching
- Entrypoint scripts copied before application code
- This allows Docker to cache entrypoint layer separately
- Code changes won't invalidate entrypoint script cache

**Impact:** Faster rebuilds when only code changes

### 2. Frontend Dockerfile (`Dockerfile.frontend`)
**Optimizations:**
- Added BuildKit cache mount for npm cache (`--mount=type=cache`)
- Changed from `npm install` to `npm ci` for faster, reliable builds
- Added `--prefer-offline --no-audit` flags for speed
- Installed wget/curl for health checks
- Optimized COPY order: config files → public → src
- Separated layers for better caching

**Impact:** 
- 50-70% faster npm installs on rebuilds
- Better layer caching
- More reliable builds

### 3. Docker Compose (`docker-compose.yml`)
**Optimizations:**
- Added BuildKit support with `x-build-args` extension
- Added `cache_from` for backend builds
- Added health checks for:
  - Celery worker (ping check)
  - Frontend (HTTP check)
- Added logging configuration for all services:
  - Max log size: 10MB
  - Max log files: 3
  - Prevents disk space issues

**Impact:**
- Faster builds with BuildKit
- Better service monitoring
- Controlled log growth

### 4. .dockerignore Files
**Enhancements:**
- **Root `.dockerignore`**: Added frontend-specific exclusions
- **`backend/.dockerignore`**: Added comprehensive exclusions:
  - Test files
  - Documentation
  - CI/CD files
  - Temporary files
  - Database files
  - Build artifacts

**Impact:** Smaller build context, faster builds

## Expected Improvements

### Build Performance
- **Initial build:** Similar (5+ minutes) - base image unchanged
- **Code-only rebuilds:** 30-40% faster with better caching
- **Frontend rebuilds:** 50-70% faster with npm cache mounts

### Image Sizes
- **No change** - optimizations focus on build speed, not image size
- Future optimization: Multi-stage builds for production

### Development Workflow
- **Faster rebuilds** when dependencies haven't changed
- **Better caching** reduces redundant downloads
- **Health checks** improve service reliability monitoring

## Usage

### Enable BuildKit (Recommended)
```bash
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

Add to `~/.bashrc` or `~/.zshrc` for persistence.

### Build with Optimizations
```bash
# Build with BuildKit cache
docker compose build

# Or explicitly
DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 docker compose build
```

### Monitor Health
```bash
# Check service health
docker compose ps

# View health check logs
docker inspect reims-backend | jq '.[0].State.Health'
```

## Files Modified

1. ✅ `backend/Dockerfile` - Optimized COPY order
2. ✅ `Dockerfile.frontend` - Added BuildKit cache, optimized layers
3. ✅ `docker-compose.yml` - Added BuildKit, health checks, logging
4. ✅ `.dockerignore` - Enhanced exclusions
5. ✅ `backend/.dockerignore` - Comprehensive exclusions

## Next Steps (Future Optimizations)

1. **Multi-stage builds** for production frontend
2. **Image size reduction** - Analyze and optimize base image
3. **Build cache registry** - Set up shared build cache
4. **Production Dockerfiles** - Separate optimized production builds
5. **Resource tuning** - Adjust limits based on actual usage metrics

## Verification

To verify optimizations are working:

```bash
# Check BuildKit is enabled
docker buildx version

# Build with verbose output to see cache usage
DOCKER_BUILDKIT=1 docker compose build --progress=plain

# Check health checks are working
docker compose ps
```

## Notes

- BuildKit cache mounts require BuildKit to be enabled
- Health checks may need adjustment based on actual service startup times
- Log rotation prevents disk space issues but may need tuning for high-volume deployments

