import asyncio
import os
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Route, WebSocketRoute, Mount
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect


NOVNC_ROOT = os.environ.get("NOVNC_ROOT", "/usr/share/novnc")
VNC_HOST = os.environ.get("VNC_HOST", "127.0.0.1")
VNC_PORT = int(os.environ.get("VNC_PORT", "5900"))


async def healthz(request):
    return PlainTextResponse("ok")


async def index(request):
    # Redirect to noVNC and autoconnect to our in-app WebSocket proxy
    # Use a path relative to /novnc so noVNC opens /novnc/websockify
    return RedirectResponse(url="/novnc/vnc.html?autoconnect=1&path=websockify")


async def vnc_ws_proxy(websocket: WebSocket):
    await websocket.accept()
    reader, writer = await asyncio.open_connection(VNC_HOST, VNC_PORT)

    async def ws_to_tcp():
        try:
            while True:
                try:
                    data = await websocket.receive_bytes()
                except WebSocketDisconnect:
                    break
                except Exception:
                    # Try text fallback
                    try:
                        text = await websocket.receive_text()
                        data = text.encode()
                    except WebSocketDisconnect:
                        break
                    except Exception:
                        break
                if data:
                    writer.write(data)
                    await writer.drain()
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def tcp_to_ws():
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                await websocket.send_bytes(data)
        except Exception:
            pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    await asyncio.gather(ws_to_tcp(), tcp_to_ws())


routes = [
    Route("/healthz", healthz),
    Route("/", index),
    # Let noVNC connect within the /novnc namespace by default
    WebSocketRoute("/novnc/websockify", vnc_ws_proxy),
    # Also support a root-level ws path if needed
    WebSocketRoute("/ws", vnc_ws_proxy),
]

# Serve noVNC static assets if available (after WS route so WS takes precedence)
if Path(NOVNC_ROOT).exists():
    routes.append(Mount("/novnc", app=StaticFiles(directory=NOVNC_ROOT), name="novnc"))

app = Starlette(debug=False, routes=routes)
