# --- STAGE 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install minimal build tooling required for compiling dependencies (if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Remove unnecessary cache and compiled bytecode to save space
RUN find /root/.local -type f -name '*.pyc' -delete && \
    find /root/.local -type d -name '__pycache__' -delete


# --- STAGE 2: Final Runtime ---
FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH

# Install ONLY SSL certificates needed for Discord Gateway & HTTP API connections
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy bot source code
COPY . .

CMD ["python", "bot.py"]