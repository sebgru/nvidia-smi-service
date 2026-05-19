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

COPY gpu-monitor.py /app/server.py
RUN chmod +x /app/server.py

# Run as a non-root user to limit blast radius if the process is compromised.
RUN adduser --disabled-password --gecos '' appuser
USER appuser

EXPOSE 8765

CMD ["python3", "/app/server.py"]
