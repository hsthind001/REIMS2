#!/bin/bash
# Source this file to enable BuildKit in your current shell
# Usage: source .docker/buildkit-env.sh

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

echo "✅ Docker BuildKit enabled for this shell session"

