"""Unified offline export manager (phase F7).

Coordinates exports from recorded XDF sessions to CSV, EDF+, BIDS, and NumPy formats.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from neurosync.export.bids import export_session_to_bids
from neurosync.export.csv import export_session_to_csv
from neurosync.export.edf import export_session_to_edf
from neurosync.export.numpy_export import export_session_to_npz
from neurosync.export.reader import load_session
from neurosync.export.session import ParsedSession


class ExportFormat(StrEnum):
    """Supported offline export target formats."""

    CSV = "csv"
    EDF = "edf"
    BIDS = "bids"
    NPZ = "npz"
    ALL = "all"


class ExportManager:
    """Manages offline exports from recorded XDF files."""

    def __init__(self, xdf_path: Path | str) -> None:
        self.xdf_path = Path(xdf_path)
        self._session: ParsedSession | None = None

    @property
    def session(self) -> ParsedSession:
        """Lazily loaded session representation."""
        if self._session is None:
            self._session = load_session(self.xdf_path)
        return self._session

    def export(
        self,
        target_format: ExportFormat | str,
        output_dir: Path | str,
        *,
        subject_id: str = "01",
        task_id: str = "experiment",
        session_id: str | None = None,
    ) -> dict[str, list[Path]]:
        """Export session to chosen format.

        Returns a dictionary mapping format names to lists of generated file/directory paths.
        """
        fmt = (
            ExportFormat(target_format.lower()) if isinstance(target_format, str) else target_format
        )
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        results: dict[str, list[Path]] = {}

        if fmt in (ExportFormat.CSV, ExportFormat.ALL):
            csv_files = export_session_to_csv(self.session, out)
            results["csv"] = csv_files

        if fmt in (ExportFormat.EDF, ExportFormat.ALL):
            edf_file = out / f"{self.session.session_id}.edf"
            res_edf = export_session_to_edf(self.session, edf_file)
            results["edf"] = [res_edf]

        if fmt in (ExportFormat.BIDS, ExportFormat.ALL):
            bids_root = out / "bids"
            res_bids = export_session_to_bids(
                self.session,
                bids_root,
                subject_id=subject_id,
                task_id=task_id,
                session_id=session_id,
            )
            results["bids"] = [res_bids]

        if fmt in (ExportFormat.NPZ, ExportFormat.ALL):
            npz_file = out / f"{self.session.session_id}.npz"
            res_npz = export_session_to_npz(self.session, npz_file)
            results["npz"] = [res_npz]

        return results
