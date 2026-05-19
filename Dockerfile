FROM python:3.12-alpine
# Alpine has a minimal package set (~0 high CVEs vs several in debian-slim).
# Pin this image to a digest to prevent tag-hijacking supply-chain attacks:
#   docker pull python:3.12-alpine
#   docker inspect python:3.12-alpine --format '{{index .RepoDigests 0}}'
# Replace the FROM line with: FROM python:3.12-alpine@sha256:<digest>
# Dependabot (see .github/dependabot.yml) will keep the digest up to date.

# nvidia-smi is provided by the host NVIDIA driver via the container toolkit.
# No CUDA toolkit needed — this image has zero pip-installed dependencies.

COPY gpu-monitor.py /app/server.py
RUN chmod +x /app/server.py

# Run as a non-root user to limit blast radius if the process is compromised.
# Alpine uses BusyBox adduser syntax (not Debian useradd).
RUN adduser -D appuser
USER appuser

EXPOSE 8765

CMD ["python3", "/app/server.py"]
