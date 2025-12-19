# Docker BuildKit Setup Guide

## What is BuildKit?

Docker BuildKit is an improved backend for building Docker images with:
- ⚡ **Faster builds** with advanced caching
- 🔄 **Parallel layer builds**
- 💾 **Better cache management**
- 🔐 **Build secrets support**
- 📦 **Cache mounts** (used in frontend Dockerfile)

## Quick Enable

### Option 1: Run Setup Script (Recommended)
```bash
./scripts/enable-buildkit.sh
source ~/.bashrc  # Or restart terminal
```

### Option 2: Manual Setup
```bash
# Enable for current session
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Add to ~/.bashrc for persistence
echo 'export DOCKER_BUILDKIT=1' >> ~/.bashrc
echo 'export COMPOSE_DOCKER_CLI_BUILD=1' >> ~/.bashrc
source ~/.bashrc
```

### Option 3: Source Helper Script
```bash
source .docker/buildkit-env.sh
```

## Verify BuildKit is Enabled

```bash
# Check BuildKit version
docker buildx version

# Should show: github.com/docker/buildx v0.x.x
```

## Usage

Once enabled, BuildKit works automatically with:

```bash
# Build with BuildKit
docker compose build

# Or explicitly
DOCKER_BUILDKIT=1 docker compose build
```

## Benefits for REIMS2

### Frontend Builds
- **npm cache mounts** - 50-70% faster npm installs
- **Layer caching** - Config files cached separately from source

### Backend Builds
- **Better caching** - Entrypoint scripts cached separately
- **Parallel builds** - Multiple services build faster

### General
- **Faster rebuilds** - Only changed layers rebuild
- **Better cache hits** - More efficient cache usage

## Troubleshooting

### BuildKit not working?
```bash
# Check if enabled
echo $DOCKER_BUILDKIT  # Should output: 1

# Re-enable
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Verify
docker buildx version
```

### Cache not working?
- Ensure BuildKit is enabled before building
- First build will be slower (populating cache)
- Subsequent builds use cache

## Notes

- BuildKit is backward compatible
- Works with all existing Docker commands
- No changes needed to Dockerfiles (already optimized)
- Cache mounts require BuildKit (used in frontend Dockerfile)

