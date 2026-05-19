#!/usr/bin/env python3
"""Unit tests for GPU monitor parsing logic — no GPU or running server required."""

import importlib.util
import pathlib

import pytest

# gpu-monitor.py has a hyphen so it cannot be imported with a normal import statement.
_spec = importlib.util.spec_from_file_location(
    "gpu_monitor",
    pathlib.Path(__file__).parent.parent / "gpu-monitor.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

parse_gpu_csv = _mod.parse_gpu_csv
parse_process_csv = _mod.parse_process_csv
GPU_FIELDS = _mod.GPU_FIELDS
_ALLOWED_QUERY_FIELDS = _mod._ALLOWED_QUERY_FIELDS

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------
# Matches the 12-field format produced by GPU_FIELDS:
# index, name, pci_bus_id, mem.used, mem.total, util.gpu, util.mem,
# temp, power, pcie.gen, pcie.width, fan
_GPU_LINE = (
    "0, NVIDIA GeForce RTX 4090, 00000000:01:00.0, 1024, 24576, 45, 30, 65, 120.5, 4, 16, 28"
)
_PROC_LINE = "1234, python3, 00000000:01:00.0, 2048"


# ---------------------------------------------------------------------------
# parse_gpu_csv
# ---------------------------------------------------------------------------
class TestParseGpuCsv:
    def test_single_gpu_fields(self):
        gpus = parse_gpu_csv(_GPU_LINE)
        assert len(gpus) == 1
        g = gpus[0]
        assert g["index"] == 0
        assert g["name"] == "NVIDIA GeForce RTX 4090"
        assert g["pci_bus_id"] == "00000000:01:00.0"
        assert g["memory_mb"]["used"] == 1024
        assert g["memory_mb"]["total"] == 24576
        assert g["memory_mb"]["free"] == 24576 - 1024
        assert g["utilization_pct"]["gpu"] == 45
        assert g["utilization_pct"]["memory"] == 30
        assert g["temperature_c"] == 65
        assert g["power_w"] == pytest.approx(120.5)
        assert g["pcie"]["gen"] == "4"
        assert g["pcie"]["width"] == "16"
        assert g["fan_pct"] == "28"

    def test_multiple_gpus(self):
        second = _GPU_LINE.replace("0,", "1,", 1)
        gpus = parse_gpu_csv(f"{_GPU_LINE}\n{second}")
        assert len(gpus) == 2
        assert gpus[1]["index"] == 1

    def test_empty_input(self):
        assert parse_gpu_csv("") == []

    def test_blank_lines_skipped(self):
        assert parse_gpu_csv("\n\n") == []

    def test_short_line_skipped(self):
        # Fewer than 11 fields — must be ignored
        assert parse_gpu_csv("0, only, three, fields") == []

    def test_non_integer_values_default_to_zero(self):
        bad = "N/A, GPU, bus, N/A, N/A, N/A, N/A, N/A, N/A, N/A, N/A"
        g = parse_gpu_csv(bad)[0]
        assert g["index"] == 0
        assert g["memory_mb"]["used"] == 0
        assert g["power_w"] == pytest.approx(0.0)

    def test_missing_fan_field_defaults_to_na(self):
        # Only 11 fields — no fan speed column
        line = "0, GPU, bus, 100, 1000, 10, 5, 50, 80.0, 4, 16"
        assert parse_gpu_csv(line)[0]["fan_pct"] == "N/A"

    def test_whitespace_stripped(self):
        padded = "  0 ,  My GPU  ,  bus  , 0 , 100 , 0 , 0 , 40 , 50.0 , 4 , 8 , 30 "
        assert parse_gpu_csv(padded)[0]["name"] == "My GPU"

    def test_memory_free_computed_correctly(self):
        g = parse_gpu_csv(_GPU_LINE)[0]
        assert g["memory_mb"]["free"] == g["memory_mb"]["total"] - g["memory_mb"]["used"]


# ---------------------------------------------------------------------------
# parse_process_csv
# ---------------------------------------------------------------------------
class TestParseProcessCsv:
    def test_single_process(self):
        procs = parse_process_csv(_PROC_LINE)
        assert len(procs) == 1
        p = procs[0]
        assert p["pid"] == "1234"
        assert p["process_name"] == "python3"
        assert p["gpu_bus_id"] == "00000000:01:00.0"
        assert p["used_memory_mb"] == "2048"

    def test_empty_input(self):
        assert parse_process_csv("") == []

    def test_short_line_skipped(self):
        assert parse_process_csv("1234, short") == []

    def test_multiple_processes(self):
        lines = f"{_PROC_LINE}\n5678, jupyter, 00000000:01:00.0, 512"
        procs = parse_process_csv(lines)
        assert len(procs) == 2
        assert procs[1]["pid"] == "5678"

    def test_blank_lines_skipped(self):
        lines = f"{_PROC_LINE}\n\n{_PROC_LINE}"
        assert len(parse_process_csv(lines)) == 2


# ---------------------------------------------------------------------------
# Allowlist integrity
# ---------------------------------------------------------------------------
class TestAllowedQueryFields:
    def test_all_default_gpu_fields_are_in_allowlist(self):
        """Every field in GPU_FIELDS (the default query) must pass the allowlist check."""
        for field in GPU_FIELDS.replace("\n", "").split(","):
            assert field.strip() in _ALLOWED_QUERY_FIELDS, (
                f"Default GPU field {field!r} is missing from _ALLOWED_QUERY_FIELDS"
            )

    def test_common_fields_present(self):
        required = {
            "index",
            "name",
            "memory.used",
            "memory.total",
            "utilization.gpu",
            "temperature.gpu",
            "power.draw",
            "fan.speed",
        }
        assert required <= _ALLOWED_QUERY_FIELDS

    def test_arbitrary_string_not_allowed(self):
        assert "rm -rf /" not in _ALLOWED_QUERY_FIELDS
        assert "$(whoami)" not in _ALLOWED_QUERY_FIELDS
        assert "" not in _ALLOWED_QUERY_FIELDS
