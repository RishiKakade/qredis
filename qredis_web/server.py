import asyncio
import os

from hypercorn.asyncio import serve as hypercorn_serve
from hypercorn.config import Config as HypercornConfig

from .app import app  # FastAPI app, startup reads REDIS_URL if set


if __name__ == "__main__":
    # Allow running the app directly with: python -m qredis_web.server
    port = int(os.getenv("PORT", "8080"))
    config = HypercornConfig()
    config.bind = [f"[::]:{port}"]  # Railway private networking (IPv6)
    asyncio.run(hypercorn_serve(app, config))

