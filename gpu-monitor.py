#!/usr/bin/env python3
"""Read-only GPU monitoring HTTP server.
Exposes nvidia-smi data as JSON. No write/mutation endpoints.

Usage: python3 server.py [--port 8765]
"""
import http.server
import json
import os
import subprocess
import sys
import urllib.parse

PORT = int(os.environ.get("GPU_MONITOR_PORT", "8765"))


def run_nvidia_smi(*args):
    """Run nvidia-smi with given args, return parsed output."""
    cmd = ["nvidia-smi"] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        return {"ok": True, "output": result.stdout.strip()}
    except subprocess.TimeoutExpired:
        return {"error": "nvidia-smi timed out"}
    except FileNotFoundError:
        return {"error": "nvidia-smi not found — is NVIDIA container runtime enabled?"}
    except Exception as e:
        return {"error": str(e)}


def parse_gpu_csv(output):
    """Parse nvidia-smi CSV into list of GPU dicts."""
    gpus = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 11:
            continue
        def int_or_0(v):
            try: return int(v)
            except: return 0
        def float_or_0(v):
            try: return float(v)
            except: return 0.0
        gpus.append({
            "index": int_or_0(parts[0]),
            "name": parts[1],
            "pci_bus_id": parts[2],
            "memory_mb": {
                "used": int_or_0(parts[3]),
                "total": int_or_0(parts[4]),
                "free": int_or_0(parts[4]) - int_or_0(parts[3]),
            },
            "utilization_pct": {
                "gpu": int_or_0(parts[5]),
                "memory": int_or_0(parts[6]),
            },
            "temperature_c": int_or_0(parts[7]),
            "power_w": float_or_0(parts[8]),
            "pcie": {
                "gen": parts[9],
                "width": parts[10],
            },
            "fan_pct": parts[11] if len(parts) > 11 else "N/A",
        })
    return gpus


def parse_process_csv(output):
    """Parse nvidia-smi compute apps CSV."""
    procs = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        procs.append({
            "pid": parts[0],
            "process_name": parts[1],
            "gpu_bus_id": parts[2],
            "used_memory_mb": parts[3],
        })
    return procs


GPU_FIELDS = (
    "index,name,pci.bus_id,memory.used,memory.total,"
    "utilization.gpu,utilization.memory,temperature.gpu,"
    "power.draw,pcie.link.gen.current,pcie.link.width.current,"
    "fan.speed"
)


class GPUHandler(http.server.BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode() + b"\n")

    def _error(self, status, msg):
        self._json({"ok": False, "error": msg}, status)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Health
        if path in ("", "/", "/health"):
            root = run_nvidia_smi("--version")
            if "error" in root:
                return self._json({
                    "ok": True,
                    "service": "gpu-monitor",
                    "nvidia_smi": False,
                    "error": root["error"],
                })
            return self._json({
                "ok": True,
                "service": "gpu-monitor",
                "nvidia_smi": True,
                "driver_version": root.get("output", "").strip(),
                "endpoints": {
                    "GET /": "this help",
                    "GET /health": "health check",
                    "GET /version": "nvidia driver + CUDA version",
                    "GET /gpus": "all GPU stats as JSON array",
                    "GET /gpu/{index}": "single GPU",
                    "GET /processes": "running GPU processes",
                    "GET /query?fields=...": "custom nvidia-smi query fields",
                },
            })

        # Version
        if path == "/version":
            data = run_nvidia_smi("--version")
            return self._json(data)

        # All GPUs
        if path == "/gpus":
            data = run_nvidia_smi(f"--query-gpu={GPU_FIELDS}", "--format=csv,noheader,nounits")
            if "error" in data:
                return self._json(data)
            return self._json({"ok": True, "gpus": parse_gpu_csv(data["output"])})

        # Single GPU
        if path.startswith("/gpu/"):
            idx = path.split("/")[-1]
            data = run_nvidia_smi(f"--id={idx}", f"--query-gpu={GPU_FIELDS}", "--format=csv,noheader,nounits")
            if "error" in data:
                return self._json(data)
            gpus = parse_gpu_csv(data["output"])
            if gpus:
                return self._json({"ok": True, "gpu": gpus[0]})
            return self._json({"ok": False, "error": f"GPU {idx} not found"}, 404)

        # Processes
        if path == "/processes":
            data = run_nvidia_smi(
                "--query-compute-apps=pid,process_name,gpu_bus_id,used_memory",
                "--format=csv,noheader,nounits"
            )
            if "error" in data:
                return self._json(data)
            return self._json({"ok": True, "processes": parse_process_csv(data["output"])})

        # Custom query
        if path == "/query":
            params = urllib.parse.parse_qs(parsed.query)
            fields = params.get("fields", [GPU_FIELDS])[0]
            data = run_nvidia_smi(f"--query-gpu={fields}", "--format=csv,noheader,nounits")
            if "error" in data:
                return self._json(data)
            return self._json({"ok": True, "fields": fields, "data": data["output"]})

        self._error(404, f"Unknown endpoint: {path}")

    def do_POST(self):
        self._error(405, "POST not allowed — read-only service")

    def log_message(self, fmt, *args):
        pass  # Stay quiet


if __name__ == "__main__":
    if "--port" in sys.argv:
        PORT = int(sys.argv[sys.argv.index("--port") + 1])
    server = http.server.HTTPServer(("0.0.0.0", PORT), GPUHandler)
    print(f"✅ GPU Monitor running on port {PORT}")
    server.serve_forever()
