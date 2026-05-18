FROM python:3.12-slim

# nvidia-smi is provided by the host NVIDIA driver via the container toolkit.
# No CUDA toolkit needed.

COPY gpu-monitor.py /app/server.py
RUN chmod +x /app/server.py

EXPOSE 8765

CMD ["python3", "/app/server.py"]
