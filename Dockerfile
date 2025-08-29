# Railway deployment container for QRedis (PyQt) exposed over HTTPS via Hypercorn + noVNC
FROM python:3.11-slim

# System deps for X11/Qt and VNC/noVNC
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11vnc novnc fluxbox \
    libxkbcommon-x11-0 libxtst6 libxrender1 libxext6 libsm6 libgl1 libglib2.0-0 \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install app and web deps
COPY . /app
# Install the project (Qt deps come via PyPI: PyQt5)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . && \
    pip install --no-cache-dir starlette hypercorn

# Environment
ENV PYTHONUNBUFFERED=1 \
    DISPLAY=:0 \
    VNC_PORT=5900 \
    NOVNC_ROOT=/usr/share/novnc \
    QT_QPA_PLATFORM=xcb

# Copy entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Railway provides $PORT; Hypercorn will bind to it
EXPOSE 8000

CMD ["/entrypoint.sh"]
