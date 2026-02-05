# Makefile for Trading Bot Application

.PHONY: setup test run build-docker run-docker clean help

# Default target
help:
	@echo "Trading Bot Management Commands"
	@echo "==============================="
	@echo "make setup        - Install dependencies (backend & frontend)"
	@echo "make test         - Run all tests"
	@echo "make run          - Start the backend application locally (using start.sh)"
	@echo "make run-frontend - Start the frontend application locally"
	@echo "make build-docker - Build the production Docker image"
	@echo "make run-docker   - Run the application via Docker Compose"
	@echo "make db-migrate   - Run database migrations"
	@echo "make db-revision  - Create a new database migration (requires message='...')"
	@echo "make check-env    - Verify .env file exists based on template"
	@echo "make clean        - Remove temporary files and build artifacts"
	@echo "make health       - Run the health check script against localhost"

setup: check-env
	@echo "Installing Backend Dependencies..."
	pip install -r requirements.txt
	@echo "Installing Frontend Dependencies..."
	cd ui/trading-bot-ui && npm install

check-env:
	@if [ ! -f .env ]; then \
		echo "ΓÜá∩╕Å .env file not found! Copying from .env.template..."; \
		cp .env.template .env; \
		echo "Γ£à Created .env. Please update it with your actual secrets."; \
	else \
		echo "Γ£à .env file exists."; \
	fi

test:
	@echo "Running Backend Tests..."
	pytest
	@echo "Running Frontend Tests..."
	cd ui/trading-bot-ui && npm test -- --watchAll=false

run:
	@echo "Starting Backend Application..."
	./start.sh

run-frontend:
	@echo "Starting Frontend Application..."
	cd ui/trading-bot-ui && npm start

db-migrate:
	@echo "Running migrations..."
	alembic upgrade head

db-revision:
	@echo "Creating new revision..."
	alembic revision --autogenerate -m "$(message)"

build-docker:
	@echo "Building Docker Image..."
	docker build -t trading-bot:latest .

run-docker:
	@echo "Starting Production Stack..."
	docker-compose -f docker-compose.prod.yml up -d

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf ui/trading-bot-ui/build
	rm -rf ui/trading-bot-ui/node_modules

health:
	@echo "Checking System Health..."
	python scripts/health_check.py http://localhost:8000
