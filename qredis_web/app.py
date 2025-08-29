import argparse
import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from .redis import WebRedis


app = FastAPI(title="QRedis Web", version="0.1.0")

# Directories for templates/static relative to this file
BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# Global Redis instance (per-process) – configured by main() or startup
_redis: Optional[WebRedis] = None


def get_r() -> WebRedis:
    if _redis is None:
        raise RuntimeError("Redis client not initialized. Start via CLI.")
    return _redis


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def _init_from_env() -> None:
    """Optional lazy init for deployments that run `uvicorn qredis_web.app:app`.

    Reads REDIS_URL (if present) and configures a WebRedis.
    """
    global _redis
    if _redis is None:
        url = os.environ.get("REDIS_URL")
        if url:
            kwargs = _parse_redis_url(url)
            _redis = WebRedis(**kwargs)


@app.get("/api/keys")
def list_keys(pattern: str = "*", cursor: int = 0, count: int = 100) -> Dict[str, Any]:
    r = get_r()
    next_cursor, keys = r.scan(cursor=cursor, match=pattern, count=count)
    return {"cursor": next_cursor, "keys": keys}


@app.get("/api/key/{key:path}")
def get_key(key: str) -> Dict[str, Any]:
    r = get_r()
    if not r.exists(key):
        raise HTTPException(status_code=404, detail="Key not found")
    item = r.get(key)
    # Normalize complex types to JSON-friendly shapes
    value = item.value
    if isinstance(value, set):
        value = sorted(list(value))
    elif isinstance(value, bytes):
        value = value.decode()
    elif isinstance(value, tuple):
        value = list(value)
    return {
        "key": item.key,
        "type": item.type,
        "ttl": item.ttl,
        "value": value,
    }


@app.put("/api/key/{key:path}")
def put_key(key: str, body: Dict[str, Any]) -> Dict[str, Any]:
    r = get_r()
    dtype = body.get("type")
    value = body.get("value")
    ttl = body.get("ttl")

    if dtype != "string":
        raise HTTPException(status_code=400, detail="Only 'string' type updates are supported in this MVP")
    if not isinstance(value, (str, int, float)):
        raise HTTPException(status_code=400, detail="Value must be a string/number")

    r.set_string(key, str(value), ttl if isinstance(ttl, int) else None)
    item = r.get(key)
    return {"ok": True, "type": item.type, "ttl": item.ttl, "value": item.value}


@app.delete("/api/key/{key:path}")
def delete_key(key: str) -> Dict[str, Any]:
    r = get_r()
    deleted = r.delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"ok": True, "deleted": deleted}


@app.get("/api/info")
def info() -> Dict[str, Any]:
    r = get_r()
    return r.info()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Any:
    return templates.TemplateResponse("index.html", {"request": request})


def _parse_redis_url(url: Optional[str]) -> Dict[str, Any]:
    from urllib.parse import urlparse, unquote

    if not url:
        return {}
    u = urlparse(url)
    kwargs: Dict[str, Any] = {}
    scheme = (u.scheme or "").lower()
    if scheme == "unix":
        if u.path:
            kwargs["unix_socket_path"] = u.path
    else:
        if u.hostname:
            kwargs["host"] = u.hostname
        if u.port:
            kwargs["port"] = u.port
        if u.path and len(u.path) > 1:
            try:
                kwargs["db"] = int(u.path.lstrip("/"))
            except Exception:
                pass
        if u.username:
            kwargs["username"] = unquote(u.username)
        if u.password:
            kwargs["password"] = unquote(u.password)
    return kwargs


def main() -> None:
    parser = argparse.ArgumentParser(description="QRedis Web (HTTP server)")
    parser.add_argument("--listen", default="127.0.0.1:8000", help="HTTP bind address host:port (default 127.0.0.1:8000)")

    # Redis connection (mirrors GUI flags)
    parser.add_argument("--host", dest="redis_host", help="Redis host")
    parser.add_argument("-p", "--port", dest="redis_port", type=int, help="Redis port")
    parser.add_argument("-s", "--sock", dest="redis_sock", help="Redis unix socket path")
    parser.add_argument("-n", "--db", dest="redis_db", type=int, help="Redis database number")
    parser.add_argument("--redis-url", dest="redis_url", help="Redis connection URL (overrides host/port/sock/db)")
    parser.add_argument("--name", dest="client_name", default="qredis-web", help="Redis client name")

    parser.add_argument("--log-level", default="INFO", choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], help="Log level")

    args = parser.parse_args()

    # Logging
    fmt = "%(asctime)-15s %(levelname)-5s %(name)s: %(message)s"
    level = getattr(logging, args.log_level.upper())
    logging.basicConfig(format=fmt, level=level)

    # Build Redis connection kwargs
    redis_url = args.redis_url or os.environ.get("REDIS_URL")
    kwargs: Dict[str, Any] = {"client_name": args.client_name}

    if redis_url:
        kwargs.update(_parse_redis_url(redis_url))
    else:
        if args.redis_sock is not None:
            kwargs["unix_socket_path"] = args.redis_sock
        if args.redis_host is not None:
            kwargs["host"] = args.redis_host
        if args.redis_port is not None:
            kwargs["port"] = args.redis_port
        if args.redis_db is not None:
            kwargs["db"] = args.redis_db

    global _redis
    _redis = WebRedis(**kwargs)

    # Start server
    host, port_s = args.listen.split(":", 1)
    uvicorn.run(app, host=host, port=int(port_s))


if __name__ == "__main__":
    main()

