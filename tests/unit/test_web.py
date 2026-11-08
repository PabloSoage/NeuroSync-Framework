"""Unit tests for neurosync.web and web server endpoints (Phase F10)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from neurosync.server.app import create_app
from neurosync.server.engine import ServerEngine
from neurosync.server.schema import StartAcquisitionRequest
from neurosync.web import get_static_dir, get_web_dir


def test_web_assets_exist() -> None:
    """Verify that web static assets and HTML templates exist and are valid."""
    web_dir = get_web_dir()
    assert web_dir.is_dir()

    index_html = web_dir / "index.html"
    assert index_html.is_file()
    html_content = index_html.read_text(encoding="utf-8")
    assert "NeuroSync" in html_content
    assert "oscilloscopeCanvas" in html_content
    assert "psdCanvas" in html_content
    assert "btnStartAcq" in html_content
    assert "viewModeSelect" in html_content
    assert "separate" in html_content

    static_dir = get_static_dir()
    assert static_dir.is_dir()

    css_file = static_dir / "styles.css"
    assert css_file.is_file()
    assert len(css_file.read_text(encoding="utf-8")) > 100

    js_file = static_dir / "app.js"
    assert js_file.is_file()
    assert len(js_file.read_text(encoding="utf-8")) > 100


def test_web_dashboard_served_via_http() -> None:
    """Test that FastAPI serves the index HTML and static assets via HTTP."""
    engine = ServerEngine()
    app = create_app(engine)
    client = TestClient(app)

    # Root route serves index.html
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "oscilloscopeCanvas" in resp.text

    # Static CSS route
    resp_css = client.get("/static/styles.css")
    assert resp_css.status_code == 200
    assert "text/css" in resp_css.headers["content-type"]

    # Static JS route
    resp_js = client.get("/static/app.js")
    assert resp_js.status_code == 200
    assert "javascript" in resp_js.headers["content-type"]


def test_websocket_events_stream() -> None:
    """Test that /ws/events streams emitted markers in real-time."""
    engine = ServerEngine()
    app = create_app(engine)
    client = TestClient(app)

    with client.websocket_connect("/ws/events") as ws:
        # Emit a marker via engine
        engine.emit_marker(42, 1.0)

        # Receive from WebSocket
        msg = ws.receive_json()
        assert msg["code"] == 42
        assert msg["payload"]["value"] == 1.0
        assert "t_host_ns" in msg


def test_websocket_stream_pre_acquisition_connection() -> None:
    """Test that /ws/stream can connect prior to acquisition and streams once started."""
    engine = ServerEngine()
    app = create_app(engine)
    client = TestClient(app)

    with client.websocket_connect("/ws/stream?format=json") as ws:
        # Start acquisition with synthetic board
        engine.start_acquisition(
            StartAcquisitionRequest(
                board_id=-1,
            )
        )

        # Receive streamed chunks
        msg_str = ws.receive_text()
        msg = json.loads(msg_str)
        assert msg["n_channels"] > 0
        assert msg["n_samples"] > 0
        assert len(msg["data"]) == msg["n_channels"]

        engine.stop_acquisition()
