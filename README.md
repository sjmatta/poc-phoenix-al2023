# Arize Phoenix on Amazon Linux 2023

A Docker container for [Arize Phoenix](https://phoenix.arize.com/) built on Amazon Linux 2023.

Phoenix is an open-source AI observability platform for LLM applications.

## Quick Start

```bash
# Build and run Phoenix
make build
make run

# Phoenix will be available at http://localhost:6006

# Send test telemetry data
make test

# Stop when done
make stop
```

## Manual Commands

```bash
# Build and run
docker-compose up -d

# Stop
docker-compose down
```

## What's Included

- **Amazon Linux 2023** base image
- **Python 3.11** 
- **Arize Phoenix** with PostgreSQL support
- **Persistent storage** with Docker volumes
- **All ports exposed**: 6006 (UI), 4317 (gRPC), 9090 (Prometheus)

## Testing

The `send_telemetry.py` script sends sample OpenTelemetry traces:

```bash
pip install -r requirements.txt
python send_telemetry.py
```

## Verification

To verify it's running on Amazon Linux 2023:

```bash
docker exec phoenix-al2023 cat /etc/os-release
```

## License

MIT License - see [LICENSE](LICENSE) file.