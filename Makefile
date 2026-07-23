.PHONY: help build up down logs clean test deploy

help:
	@echo "Available commands:"
	@echo "  make build     - Build Docker images"
	@echo "  make up        - Start services with Docker Compose"
	@echo "  make down      - Stop services"
	@echo "  make logs      - View logs"
	@echo "  make clean     - Clean up containers and volumes"
	@echo "  make test      - Run tests"
	@echo "  make deploy    - Deploy to Kubernetes"

build:
	docker-compose -f docker/docker-compose.yaml build

up:
	docker-compose -f docker/docker-compose.yaml up -d
	@echo "Services started. Access at:"
	@echo "  Envoy: http://localhost:8080"
	@echo "  Control Plane: http://localhost:8000"
	@echo "  Grafana: http://localhost:3000 (admin/admin)"

down:
	docker-compose -f docker/docker-compose.yaml down

logs:
	docker-compose -f docker/docker-compose.yaml logs -f

clean:
	docker-compose -f docker/docker-compose.yaml down -v
	docker system prune -f

test:
	pytest tests/ -v --cov=src --cov-report=html

deploy:
	./scripts/deploy.sh k8s

dev:
	uvicorn src.main:app --host 0.0.0.0 --port 9000 --reload

lint:
	flake8 src/
	black src/ --check
	isort src/ --check-only

format:
	black src/
	isort src/

install:
	pip install -r requirements.txt
	python -m spacy download en_core_web_sm
