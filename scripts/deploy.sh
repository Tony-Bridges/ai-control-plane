#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying AI Control Plane${NC}"

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker is required but not installed. Aborting.${NC}" >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo -e "${YELLOW}kubectl not found. Skipping K8s deployment.${NC}"; }

# Build Docker images
echo -e "${YELLOW}Building Docker images...${NC}"
docker build -t ai-control-plane:latest -f docker/Dockerfile .
docker build -t envoy-gateway:latest -f docker/Dockerfile.envoy .

# Deploy with Docker Compose
if [ "$1" == "docker" ]; then
    echo -e "${YELLOW}Deploying with Docker Compose...${NC}"
    docker-compose -f docker/docker-compose.yaml up -d

    echo -e "${GREEN}✅ Deployment complete!${NC}"
    echo -e "Services:"
    echo -e "  - Envoy Gateway: http://localhost:8080"
    echo -e "  - Control Plane: http://localhost:8000"
    echo -e "  - OPA: http://localhost:8181"
    echo -e "  - Prometheus: http://localhost:9090"
    echo -e "  - Grafana: http://localhost:3000 (admin/admin)"
    exit 0
fi

# Deploy to Kubernetes
if [ "$1" == "k8s" ] || [ -z "$1" ]; then
    echo -e "${YELLOW}Deploying to Kubernetes...${NC}"

    # Create namespace
    kubectl create namespace ai-gateway --dry-run=client -o yaml | kubectl apply -f -

    # Apply secrets
    echo -e "${YELLOW}Creating secrets...${NC}"
    kubectl create secret generic model-secrets \
        --from-literal=openai-key=${OPENAI_API_KEY:-""} \
        --from-literal=azure-key=${AZURE_OPENAI_API_KEY:-""} \
        --from-literal=anthropic-key=${ANTHROPIC_API_KEY:-""} \
        --namespace ai-gateway --dry-run=client -o yaml | kubectl apply -f -

    kubectl create secret generic postgres-secrets \
        --from-literal=username=${POSTGRES_USER:-audit_user} \
        --from-literal=password=${POSTGRES_PASSWORD:-audit_pass} \
        --from-literal=database=${POSTGRES_DB:-aiaudit} \
        --namespace ai-gateway --dry-run=client -o yaml | kubectl apply -f -

    # Apply ConfigMaps
    echo -e "${YELLOW}Creating ConfigMaps...${NC}"
    kubectl apply -f k8s/envoy/envoy-configmap.yaml
    kubectl apply -f k8s/control-plane/configmap.yaml

    # Apply deployments
    echo -e "${YELLOW}Deploying services...${NC}"
    kubectl apply -f k8s/control-plane/deployment.yaml
    kubectl apply -f k8s/control-plane/service.yaml
    kubectl apply -f k8s/control-plane/hpa.yaml
    kubectl apply -f k8s/envoy/envoy-deployment.yaml
    kubectl apply -f k8s/envoy/envoy-service.yaml
    kubectl apply -f k8s/opa/opa-deployment.yaml
    kubectl apply -f k8s/redis/redis-deployment.yaml
    kubectl apply -f k8s/postgres/postgres-deployment.yaml

    # Wait for deployments
    echo -e "${YELLOW}Waiting for deployments to be ready...${NC}"
    kubectl rollout status deployment/ai-control-plane -n ai-gateway
    kubectl rollout status deployment/envoy -n ai-gateway

    # Get service IP
    echo -e "${GREEN}✅ Deployment complete!${NC}"
    echo -e "Services:"
    kubectl get svc -n ai-gateway

    # Port-forward for local access
    echo -e "${YELLOW}To access services locally:${NC}"
    echo -e "  kubectl port-forward -n ai-gateway service/envoy-service 8080:8080"
    echo -e "  kubectl port-forward -n ai-gateway service/ai-control-plane-service 8000:8000"
fi

# Database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python scripts/migrate_db.py

# Seed initial policies
echo -e "${YELLOW}Seeding initial policies...${NC}"
python scripts/seed_policies.py

echo -e "${GREEN}✅ All done!${NC}"
