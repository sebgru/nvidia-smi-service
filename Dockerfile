FROM python:3.14-slim
# Debian-based slim image — required because nvidia-smi is a glibc binary
# injected by the NVIDIA Container Toolkit, and Alpine (musl libc) cannot run it.
#
# Pin this image to a digest to prevent tag-hijacking supply-chain attacks:
#   docker pull python:3.14-slim
#   docker inspect python:3.14-slim --format '{{index .RepoDigests 0}}'
# Replace the FROM line with: FROM python:3.14-slim@sha256:<digest>
# Dependabot (see .github/dependabot.yml) will keep the digest up to date.

# nvidia-smi is provided by the host NVIDIA driver via the container toolkit.
# No CUDA toolkit needed — this image has zero pip-installed dependencies.

# Update all system packages to their latest security-patched versions
# to minimize HIGH/CRITICAL CVEs (trivy CI gate with --ignore-unfixed).
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

COPY gpu-monitor.py /app/server.py
RUN chmod +x /app/server.py

# Run as a non-root user to limit blast radius if the process is compromised.
RUN adduser --disabled-password --gecos '' appuser
USER appuser

ENV GPU_MONITOR_PORT=8765
# Default port is 8765; override at runtime with -e GPU_MONITOR_PORT=<port>.
# EXPOSE is intentionally omitted — a hardcoded value would be misleading here.

# python3 is always available in this image; no curl needed.
# The health endpoint returns 200 regardless of nvidia-smi availability,
# so this check tests only that the HTTP server is responsive.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${GPU_MONITOR_PORT}/health', timeout=4)" || exit 1

CMD ["python3", "/app/server.py"]
