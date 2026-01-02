# Makefile for Trading Bot Application

.PHONY: setup test run build-docker run-docker clean help

# Default target
help:
	@echo "Trading Bot Management Commands"
	@echo "==============================="
	@echo "make setup        - Install dependencies (backend & frontend)"
	@echo "make test         - Run all tests"
	@echo "make run          - Start the application locally (using start.sh)"
	@echo "make build-docker - Build the production Docker image"
	@echo "make run-docker   - Run the application via Docker Compose"
	@echo "make clean        - Remove temporary files and build artifacts"
	@echo "make health       - Run the health check script against localhost"

setup:
	@echo "Installing Backend Dependencies..."
	pip install -r requirements.txt
	@echo "Installing Frontend Dependencies..."
	cd ui/trading-bot-ui && npm install

test:
	@echo "Running Backend Tests..."
	pytest
	@echo "Running Frontend Tests..."
	cd ui/trading-bot-ui && npm test -- --watchAll=false

run:
	@echo "Starting Application..."
	./start.sh

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
