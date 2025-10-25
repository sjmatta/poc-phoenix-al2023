# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains Arize Phoenix on Amazon Linux 2023 - a Docker container for the open-source AI observability platform. Phoenix is designed for monitoring LLM applications with OpenTelemetry integration.

## Common Commands

### Quick Start
```bash
# Build and run Phoenix
make build
make run

# Send test telemetry data
make test

# Stop when done
make stop
```

### Development Commands
```bash
# Build Docker image
make build
docker-compose build

# Run container in background
make run
docker-compose up -d

# View logs
make logs
docker-compose logs -f

# Open shell in container
make shell
docker exec -it phoenix-al2023 /bin/bash

# Stop container
make stop
docker-compose down

# Clean up everything (containers, images, volumes)
make clean
docker-compose down -v --rmi all

# Send test telemetry
make test
python3 send_telemetry.py
```

### Testing the Installation
```bash
# Verify Phoenix is running on Amazon Linux 2023
docker exec phoenix-al2023 cat /etc/os-release

# Check Phoenix UI (should be available after startup)
curl http://localhost:6006

# Install dependencies for telemetry testing
pip3 install -r requirements.txt
```

## Architecture

The repository has two main components:

1. **Main Phoenix Container**: A dockerized Phoenix instance on Amazon Linux 2023
   - Base image: `amazonlinux:2023` (version 2023.7.20250331)
   - Python 3.13 with Arize Phoenix 12.7.0+
   - PostgreSQL support enabled
   - Ports: 6006 (UI), 4317 (gRPC), 9090 (Prometheus)

2. **LLM Microservices Example** (`examples/llm-service/`): A complete demonstration showing:
   - API Gateway (port 8080)
   - LLM Service (port 8000) 
   - Vector Store (port 8001)
   - Phoenix observability integration

## Key Files

- `Dockerfile`: Amazon Linux 2023 base with Phoenix installation
- `docker-compose.yml`: Phoenix service configuration with health checks
- `send_telemetry.py`: Test script that sends sample OpenTelemetry traces
- `Makefile`: Common operations (build, run, test, clean)
- `examples/llm-service/`: Complete microservices demo with realistic LLM observability

## LLM Services Example

The `examples/llm-service/` directory contains a production-ready example with:

### Starting the Example
```bash
cd examples/llm-service
docker-compose up -d

# Test the API
python test_api.py

# Manual API test
curl -X POST http://localhost:8080/api/v1/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-token" \
  -d '{"question": "What is artificial intelligence?"}'

# Generate load for demo
docker-compose --profile load-test up load-generator
```

### Services Architecture
- **API Gateway** (8080): Authentication, rate limiting, request routing
- **LLM Service** (8000): Q&A processing with mock LLM calls
- **Vector Store** (8001): Document similarity search and embeddings
- **Phoenix** (6006): Observability dashboard

All services automatically send traces to Phoenix showing request flow, LLM token usage, vector search metrics, and error tracking.

## OpenTelemetry Integration

Phoenix receives traces via:
- HTTP endpoint: `http://localhost:6006/v1/traces`
- gRPC endpoint: `localhost:4317`

The test script demonstrates proper OpenTelemetry setup with:
- LLM call tracing with token usage
- Vector search operations
- Error simulation and tracking
- Custom span attributes for AI applications

## Container Details

- **Base**: Amazon Linux 2023
- **User**: Non-root user (nonroot, uid 65532)
- **Working Directory**: `/mnt/data` (persistent volume)
- **Environment**: `PHOENIX_WORKING_DIR=/mnt/data`
- **Health Check**: Curl to `http://localhost:6006/`