"""Service runner and entrypoint for neurosyncd (phase F8)."""

from __future__ import annotations

import uvicorn

from neurosync.server.app import create_app
from neurosync.server.engine import ServerEngine


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    engine: ServerEngine | None = None,
    log_level: str = "info",
) -> None:
    """Run neurosyncd ASGI application using uvicorn."""
    app = create_app(engine)
    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    run_server()
