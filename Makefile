# Makefile for Video Generation App

.PHONY: help dev staging prod stop clean logs

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev: ## Start development environment
	@echo "Starting development environment..."
	docker-compose -f docker-compose.dev.yml up --build

dev-d: ## Start development environment in detached mode
	@echo "Starting development environment in detached mode..."
	docker-compose -f docker-compose.dev.yml up -d --build

staging: ## Start staging environment
	@echo "Starting staging environment..."
	docker-compose -f docker-compose.yml --env-file .env.staging up --build

staging-d: ## Start staging environment in detached mode
	@echo "Starting staging environment in detached mode..."
	docker-compose -f docker-compose.yml --env-file .env.staging up -d --build

prod: ## Start production environment
	@echo "Starting production environment..."
	docker-compose -f docker-compose.prod.yml up --build

prod-d: ## Start production environment in detached mode
	@echo "Starting production environment in detached mode..."
	docker-compose -f docker-compose.prod.yml up -d --build

stop: ## Stop all services
	@echo "Stopping all services..."
	docker-compose -f docker-compose.dev.yml down || true
	docker-compose -f docker-compose.yml down || true
	docker-compose -f docker-compose.prod.yml down || true

clean: ## Clean up volumes and containers
	@echo "Cleaning up..."
	docker-compose -f docker-compose.dev.yml down -v || true
	docker-compose -f docker-compose.yml down -v || true
	docker-compose -f docker-compose.prod.yml down -v || true

logs: ## Show logs for all services
	docker-compose -f docker-compose.dev.yml logs -f

logs-web: ## Show logs for web service
	docker-compose -f docker-compose.dev.yml logs -f web

logs-worker: ## Show logs for worker service
	docker-compose -f docker-compose.dev.yml logs -f worker

logs-frontend: ## Show logs for frontend service
	docker-compose -f docker-compose.dev.yml logs -f frontend

shell-web: ## Open shell in web container
	docker-compose -f docker-compose.dev.yml exec web /bin/bash

shell-worker: ## Open shell in worker container
	docker-compose -f docker-compose.dev.yml exec worker /bin/bash

shell-frontend: ## Open shell in frontend container
	docker-compose -f docker-compose.dev.yml exec frontend /bin/sh

test: ## Run tests
	@echo "Running tests..."
	docker-compose -f docker-compose.dev.yml exec web pytest

lint: ## Run linters
	@echo "Running linters..."
	docker-compose -f docker-compose.dev.yml exec web flake8 app/
	docker-compose -f docker-compose.dev.yml exec frontend npm run lint

format: ## Format code
	@echo "Formatting code..."
	docker-compose -f docker-compose.dev.yml exec web black app/
	docker-compose -f docker-compose.dev.yml exec frontend npm run format
