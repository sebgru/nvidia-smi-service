# nvidia-smi-service

A lightweight read-only HTTP API wrapping `nvidia-smi` for containerized agents. Query GPU stats (memory, utilization, temperature, PCIe info) as JSON over HTTP.

Perfect for AI assistants, agentic systems, or monitoring tools that need GPU visibility but can't access `nvidia-smi` directly.

## Quick Start

### docker-compose

```yaml
services:
  nvidia-smi-service:
    image: python:3.12-slim
    container_name: nvidia-smi-service
    restart: unless-stopped
    command: ["python3", "/app/server.py"]
    volumes:
      - ./gpu-monitor.py:/app/server.py:ro
    ports:
      - "8765:8765"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

### Docker

```bash
docker build -t nvidia-smi-service .
docker run -d --gpus all -p 8765:8765 --name nvidia-smi-service nvidia-smi-service
```

### Build (optional)

```bash
docker build -t nvidia-smi-service .
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Service info and endpoint list |
| `GET /health` | Health check (reports if nvidia-smi is reachable) |
| `GET /version` | NVIDIA driver + CUDA version |
| `GET /gpus` | All GPU stats as JSON array |
| `GET /gpu/{index}` | Single GPU stats (e.g. `/gpu/0`) |
| `GET /processes` | Running GPU processes with PID, name, memory |
| `GET /query?fields=...` | Custom nvidia-smi query fields |

### Example Response: `/gpus`

```json
{
  "ok": true,
  "gpus": [
    {
      "index": 0,
      "name": "NVIDIA GeForce RTX 5060 Ti",
      "pci_bus_id": "00000000:01:00.0",
      "memory_mb": {
        "used": 5078,
        "total": 16311,
        "free": 11233
      },
      "utilization_pct": {
        "gpu": 12,
        "memory": 8
      },
      "temperature_c": 46,
      "power_w": 66.0,
      "pcie": {
        "gen": "5",
        "width": "8"
      },
      "fan_pct": "32"
    }
  ]
}
```

## Querying from another container

```bash
# Inside your container (same Docker network):
curl http://nvidia-smi-service:8765/gpus
curl http://nvidia-smi-service:8765/gpu/0
curl http://nvidia-smi-service:8765/health
```

## Permissions

- **Strictly read-only**: no POST, PUT, PATCH, or DELETE endpoints
- No system mutation, no GPU config changes
- `nvidia-smi` is already read-only by design

## Requirements

- Docker with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- NVIDIA driver (any version, `nvidia-smi` provided by the host)

## License

MIT
