# MeAI Dockerfile
FROM python:3.10-slim

# System dependencies for PyQt6, nmap, build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    nmap \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

# Default: run the API server
CMD ["python", "llm_server.py"]

# To run the desktop app, use VNC/X11 forwarding (not default in container) 