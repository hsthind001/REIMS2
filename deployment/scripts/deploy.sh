#!/bin/bash
set -e

# REIMS2 Production Deployment Script
# Usage: ./deploy.sh [environment] [action]
# Example: ./deploy.sh production deploy

ENVIRONMENT=${1:-production}
ACTION=${2:-deploy}
NAMESPACE="reims2"
KUBECTL_CMD="kubectl"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed"
        exit 1
    fi
    
    # Check Kubernetes connection
    if ! $KUBECTL_CMD cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    $KUBECTL_CMD apply -f ../kubernetes/namespace.yaml
}

# Create secrets
create_secrets() {
    log_info "Creating secrets..."
    
    if [ ! -f "../kubernetes/secrets.yaml" ]; then
        log_error "secrets.yaml not found. Please create it from secrets.yaml.template"
        exit 1
    fi
    
    $KUBECTL_CMD apply -f ../kubernetes/secrets.yaml
    log_info "Secrets created"
}

# Build and push Docker images
build_images() {
    log_info "Building Docker images..."
    
    # Build backend
    log_info "Building backend image..."
    docker build -t reims2-backend:latest -f ../../backend/Dockerfile ../../backend/
    
    # Build frontend
    log_info "Building frontend image..."
    docker build -t reims2-frontend:latest -f ../../Dockerfile.frontend.production .
    
    # Tag for registry (if using private registry)
    if [ ! -z "$DOCKER_REGISTRY" ]; then
        log_info "Tagging images for registry: $DOCKER_REGISTRY"
        docker tag reims2-backend:latest $DOCKER_REGISTRY/reims2-backend:latest
        docker tag reims2-frontend:latest $DOCKER_REGISTRY/reims2-frontend:latest
        
        log_info "Pushing images to registry..."
        docker push $DOCKER_REGISTRY/reims2-backend:latest
        docker push $DOCKER_REGISTRY/reims2-frontend:latest
    fi
}

# Deploy infrastructure (PostgreSQL, Redis, MinIO)
deploy_infrastructure() {
    log_info "Deploying infrastructure..."
    
    $KUBECTL_CMD apply -f ../kubernetes/postgresql.yaml
    $KUBECTL_CMD apply -f ../kubernetes/redis.yaml
    
    # Wait for infrastructure to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    $KUBECTL_CMD wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
    
    log_info "Waiting for Redis to be ready..."
    $KUBECTL_CMD wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s
    
    log_info "Infrastructure deployed"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Create migration job
    cat <<EOF | $KUBECTL_CMD apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration-$(date +%s)
  namespace: $NAMESPACE
spec:
  template:
    spec:
      containers:
      - name: migration
        image: reims2-backend:latest
        command:
        - alembic
        - upgrade
        - head
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        - name: POSTGRES_SERVER
          value: postgres
        - name: POSTGRES_PORT
          value: "5432"
        - name: POSTGRES_DB
          value: "reims"
      restartPolicy: Never
  backoffLimit: 3
EOF
    
    # Wait for migration to complete
    log_info "Waiting for migrations to complete..."
    sleep 10
    $KUBECTL_CMD wait --for=condition=complete job -l app=migration -n $NAMESPACE --timeout=300s || true
    
    log_info "Migrations completed"
}

# Deploy application
deploy_application() {
    log_info "Deploying application..."
    
    $KUBECTL_CMD apply -f ../kubernetes/backend.yaml
    $KUBECTL_CMD apply -f ../kubernetes/celery-worker.yaml
    $KUBECTL_CMD apply -f ../kubernetes/frontend.yaml
    
    # Wait for deployments to be ready
    log_info "Waiting for backend to be ready..."
    $KUBECTL_CMD wait --for=condition=available deployment/backend -n $NAMESPACE --timeout=300s
    
    log_info "Waiting for frontend to be ready..."
    $KUBECTL_CMD wait --for=condition=available deployment/frontend -n $NAMESPACE --timeout=300s
    
    log_info "Application deployed"
}

# Deploy monitoring
deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    
    $KUBECTL_CMD apply -f ../kubernetes/prometheus.yaml
    $KUBECTL_CMD apply -f ../kubernetes/grafana.yaml
    
    log_info "Monitoring stack deployed"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Check backend health
    BACKEND_POD=$($KUBECTL_CMD get pod -l app=backend -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
    if [ ! -z "$BACKEND_POD" ]; then
        log_info "Checking backend health endpoint..."
        $KUBECTL_CMD exec -n $NAMESPACE $BACKEND_POD -- curl -f http://localhost:8000/api/v1/health || {
            log_error "Backend health check failed"
            return 1
        }
        log_info "Backend health check passed"
    fi
    
    # Check all pods are running
    log_info "Checking pod status..."
    $KUBECTL_CMD get pods -n $NAMESPACE
    
    log_info "Health check completed"
}

# Rollback to previous version
rollback() {
    log_warn "Rolling back to previous version..."
    
    # Rollback backend
    $KUBECTL_CMD rollout undo deployment/backend -n $NAMESPACE
    $KUBECTL_CMD rollout undo deployment/celery-worker -n $NAMESPACE
    $KUBECTL_CMD rollout undo deployment/frontend -n $NAMESPACE
    
    # Wait for rollback to complete
    $KUBECTL_CMD rollout status deployment/backend -n $NAMESPACE
    $KUBECTL_CMD rollout status deployment/celery-worker -n $NAMESPACE
    $KUBECTL_CMD rollout status deployment/frontend -n $NAMESPACE
    
    log_info "Rollback completed"
}

# Main deployment flow
deploy() {
    log_info "Starting deployment to $ENVIRONMENT environment..."
    
    check_prerequisites
    create_namespace
    create_secrets
    build_images
    deploy_infrastructure
    run_migrations
    deploy_application
    deploy_monitoring
    health_check
    
    log_info "Deployment completed successfully!"
    log_info "Backend: http://backend.reims2.svc.cluster.local:8000"
    log_info "Frontend: http://frontend.reims2.svc.cluster.local"
    log_info "Grafana: http://grafana.reims2.svc.cluster.local:3000"
    log_info "Prometheus: http://prometheus.reims2.svc.cluster.local:9090"
}

# Main script
case $ACTION in
    deploy)
        deploy
        ;;
    rollback)
        rollback
        ;;
    health)
        health_check
        ;;
    *)
        log_error "Unknown action: $ACTION"
        log_info "Usage: $0 [environment] [deploy|rollback|health]"
        exit 1
        ;;
esac

