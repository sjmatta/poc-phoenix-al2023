.PHONY: help build up down logs test load-test clean health phoenix

# Default target
help:
	@echo "LLM Microservices with Phoenix Observability"
	@echo "==========================================="
	@echo "Available targets:"
	@echo "  build       - Build all Docker images"
	@echo "  up          - Start all services"
	@echo "  down        - Stop all services"
	@echo "  logs        - Show logs from all services"
	@echo "  test        - Run API tests"
	@echo "  load-test   - Generate load for demonstration"
	@echo "  health      - Check health of all services"
	@echo "  phoenix     - Open Phoenix UI in browser"
	@echo "  clean       - Stop services and remove volumes"
	@echo "  help        - Show this help message"

# Build all images
build:
	@echo "Building all Docker images..."
	docker-compose build

# Start all services
up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 30
	@echo ""
	@echo "✅ Services started successfully!"
	@echo ""
	@echo "🔍 Phoenix UI: http://localhost:6006"
	@echo "🚪 API Gateway: http://localhost:8080/health"
	@echo "🤖 LLM Service: http://localhost:8000/health"
	@echo "📊 Vector Store: http://localhost:8001/health"

# Stop all services
down:
	@echo "Stopping all services..."
	docker-compose down

# Show logs
logs:
	docker-compose logs -f

# Run API tests
test:
	@echo "Running API tests..."
	python test_api.py

# Generate load test
load-test:
	@echo "Starting load test..."
	docker-compose --profile load-test up load-generator

# Check health of all services
health:
	@echo "Checking service health..."
	@echo "Phoenix UI:"
	@curl -s -o /dev/null -w "  Status: %{http_code}\n" http://localhost:6006/ || echo "  Status: Down"
	@echo "API Gateway:"
	@curl -s -o /dev/null -w "  Status: %{http_code}\n" http://localhost:8080/health || echo "  Status: Down"
	@echo "LLM Service:"
	@curl -s -o /dev/null -w "  Status: %{http_code}\n" http://localhost:8000/health || echo "  Status: Down"
	@echo "Vector Store:"
	@curl -s -o /dev/null -w "  Status: %{http_code}\n" http://localhost:8001/health || echo "  Status: Down"

# Open Phoenix UI
phoenix:
	@echo "Opening Phoenix UI..."
	@which open >/dev/null 2>&1 && open http://localhost:6006 || echo "Open http://localhost:6006 in your browser"

# Clean up everything
clean:
	@echo "Cleaning up all containers and volumes..."
	docker-compose down -v --rmi local