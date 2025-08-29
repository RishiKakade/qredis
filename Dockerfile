# syntax=docker/dockerfile:1

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Install Python deps first (better build cache)
COPY requirements-web.txt /tmp/requirements-web.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements-web.txt

# Copy only what we need (no PyQt5 installation required)
COPY qredis_web /app/qredis_web
COPY qredis /app/qredis

# Expose default port used locally; Railway will set $PORT.
EXPOSE 8080

# Start via Hypercorn with IPv6 bind using $PORT
CMD ["python", "-m", "qredis_web.server"]
