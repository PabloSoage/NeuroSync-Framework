"""Command line interface for NeuroSync (phase F9).

Provides:
- Typer CLI with rich formatting
- NeuroSyncClient for remote daemon orchestration
"""

from __future__ import annotations

from neurosync.cli.client import NeuroSyncClient
from neurosync.cli.main import app

__all__ = ["NeuroSyncClient", "app"]
