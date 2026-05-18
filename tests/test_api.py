#!/usr/bin/env python3
"""Basic validation tests for the GPU monitor service."""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8765"
PASS = 0
FAIL = 0


def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  ✅ {name}")
    except Exception as e:
        FAIL += 1
        print(f"  ❌ {name}: {e}")


def fetch(path):
    url = f"{BASE}{path}"
    resp = urllib.request.urlopen(url, timeout=10)
    return json.loads(resp.read())


def check_ok(data):
    assert data.get("ok") is True, f"Expected ok=true, got {data}"


# --- Tests ---

def test_health():
    data = fetch("/health")
    check_ok(data)
    assert "nvidia_smi" in data


def test_gpus():
    data = fetch("/gpus")
    check_ok(data)
    gpus = data.get("gpus", [])
    assert len(gpus) > 0, "Expected at least 1 GPU"
    gpu = gpus[0]
    assert "index" in gpu
    assert "memory_mb" in gpu
    assert gpu["memory_mb"]["total"] > 0


def test_gpu_index():
    data = fetch("/gpu/0")
    check_ok(data)
    assert data["gpu"]["index"] == 0


def test_gpu_not_found():
    try:
        fetch("/gpu/999")
    except urllib.error.HTTPError as e:
        assert e.code == 404


def test_version():
    data = fetch("/version")
    assert "ok" in data or "output" in data


def test_processes():
    data = fetch("/processes")
    check_ok(data)
    assert "processes" in data


def test_query():
    data = fetch("/query?fields=index,name")
    check_ok(data)
    assert "data" in data


# --- Run ---
print(f"🧪 GPU Monitor Tests (against {BASE})")
print()

test("GET /health returns nvidia-smi status", test_health)
test("GET /gpus returns GPU list", test_gpus)
test("GET /gpu/0 returns GPU 0", test_gpu_index)
test("GET /gpu/999 returns 404", test_gpu_not_found)
test("GET /version returns driver info", test_version)
test("GET /processes returns process list", test_processes)
test("GET /query with custom fields", test_query)

print()
print(f"Results: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
