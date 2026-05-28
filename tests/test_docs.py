#!/usr/bin/env python3
"""Documentation consistency tests — verify README stays in sync with the code."""

import pathlib

_ROOT = pathlib.Path(__file__).parent.parent
_README = (_ROOT / "README.md").read_text()
_CODE = (_ROOT / "gpu-monitor.py").read_text()

# Every path that do_GET handles — if the code changes, this test enforces an update
# to the README (and vice-versa).
_IMPLEMENTED_ENDPOINTS = [
    "/health",
    "/version",
    "/gpus",
    "/gpu/",
    "/processes",
    "/query",
]


class TestDocsConsistency:
    def test_all_endpoints_documented_in_readme(self):
        """Every implemented endpoint path must appear in README.md."""
        for endpoint in _IMPLEMENTED_ENDPOINTS:
            assert endpoint in _README, (
                f"Endpoint {endpoint!r} is implemented in gpu-monitor.py "
                f"but not documented in README.md"
            )

    def test_all_documented_endpoints_implemented(self):
        """Every endpoint listed above must also exist in the source code."""
        for endpoint in _IMPLEMENTED_ENDPOINTS:
            assert endpoint in _CODE, (
                f"Endpoint {endpoint!r} is listed in test_docs.py but not "
                f"found in gpu-monitor.py — either the code was changed without "
                f"updating the docs, or the endpoint list here is stale"
            )

    def test_default_port_matches_readme(self):
        """The default port documented in README must match the code's default."""
        assert "8765" in _README, "Default port 8765 not mentioned in README.md"
        assert '"8765"' in _CODE, (
            "Default port 8765 not found as a string literal in gpu-monitor.py"
        )

    def test_readme_has_ci_badge(self):
        """README must include the CI status badge so health is always visible."""
        assert "actions/workflows/ci.yml/badge.svg" in _README, "CI badge missing from README.md"
