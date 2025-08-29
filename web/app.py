import asyncio
import os
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Route, WebSocketRoute, Mount
from starlette.staticfiles import StaticFiles


NOVNC_ROOT = os.environ.get("NOVNC_ROOT", "/usr/share/novnc")
VNC_HOST = os.environ.get("VNC_HOST", "127.0.0.1")
VNC_PORT = int(os.environ.get("VNC_PORT", "5900"))


async def healthz(request):
    return PlainTextResponse("ok")


async def index(request):
    # Redirect to the standard noVNC page with our websocket path
    # noVNC defaults to path "websockify"; we pass path=ws to match our ASGI route
    return RedirectResponse(url="/novnc/vnc.html?path=ws")


async def vnc_ws_proxy(websocket):
    await websocket.accept()
    reader, writer = await asyncio.open_connection(VNC_HOST, VNC_PORT)

    async def ws_to_tcp():
        try:
            while True:
                msg = await websocket.receive()
                if msg['type'] == 'websocket.receive':
                    data = msg.get('bytes') or msg.get('text')
                    if isinstance(data, str):
                        data = data.encode()
                    if data:
                        writer.write(data)
                        await writer.drain()
                elif msg['type'] == 'websocket.disconnect':
                    break
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
        finally:
            await websocket.close()

    await asyncio.gather(ws_to_tcp(), tcp_to_ws())


routes = [
    Route("/healthz", healthz),
    Route("/", index),
    WebSocketRoute("/ws", vnc_ws_proxy),
]

# Serve noVNC static assets if available
if Path(NOVNC_ROOT).exists():
    routes.append(Mount("/novnc", app=StaticFiles(directory=NOVNC_ROOT), name="novnc"))

app = Starlette(debug=False, routes=routes)
