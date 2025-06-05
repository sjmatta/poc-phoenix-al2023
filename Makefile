.PHONY: build run stop clean test logs shell help

# Default target
help:
	@echo "Available targets:"
	@echo "  build       - Build the Phoenix Docker image"
	@echo "  run         - Run Phoenix container in background"
	@echo "  stop        - Stop and remove Phoenix container"
	@echo "  clean       - Remove container, image, and volumes"
	@echo "  test        - Send test telemetry data"
	@echo "  logs        - Show Phoenix container logs"
	@echo "  shell       - Open shell in running container"
	@echo "  help        - Show this help message"

# Build the Docker image
build:
	@echo "Building Phoenix Docker image..."
	docker-compose build

# Run the container
run:
	@echo "Starting Phoenix container..."
	docker-compose up -d
	@echo "Waiting for Phoenix to start..."
	@sleep 10
	@echo "Phoenix is running at http://localhost:6006"

# Stop the container
stop:
	@echo "Stopping Phoenix container..."
	docker-compose down

# Clean up everything
clean:
	@echo "Cleaning up containers, images, and volumes..."
	docker-compose down -v --rmi all

# Send test telemetry
test:
	@echo "Sending test telemetry data..."
	@pip3 install -r requirements.txt > /dev/null 2>&1
	@python3 send_telemetry.py

# Show logs
logs:
	docker-compose logs -f

# Open shell in container
shell:
	docker exec -it phoenix-al2023 /bin/bash