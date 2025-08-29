#!/usr/bin/env bash
set -euo pipefail

# Defaults
export DISPLAY=":0"
VNC_PORT="${VNC_PORT:-5900}"
PORT="${PORT:-8000}"
SCREEN_WIDTH="${SCREEN_WIDTH:-1280}"
SCREEN_HEIGHT="${SCREEN_HEIGHT:-800}"

# Ensure Qt uses X11
export QT_QPA_PLATFORM="xcb"

# Start X virtual framebuffer
Xvfb :0 -screen 0 ${SCREEN_WIDTH}x${SCREEN_HEIGHT}x24 &
XVFB_PID=$!

# Optional lightweight window manager (helps some widgets behave correctly)
if command -v fluxbox >/dev/null 2>&1; then
  fluxbox &
fi

# Start the Qt app (QRedis)
python -m qredis &
QREDIS_PID=$!

# Start VNC server attached to the Xvfb display
x11vnc -display :0 -forever -shared -nopw -rfbport ${VNC_PORT} -xkb -ncache 10 &
X11VNC_PID=$!

# Start Hypercorn (serves noVNC and WS proxy) bound to assigned $PORT
exec hypercorn --bind 0.0.0.0:${PORT} web.app:app
