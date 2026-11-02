"""Architecture rules checked by reading the code (phase F1).

If one of these tests fails, do not "fix" the test: fix the code. The rules
come from ``docs/decisions.md``.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "neurosync"

#: The only file allowed to read wall-clock time (D-02).
WALL_CLOCK_ALLOWED = {SRC / "core" / "anchors.py"}

#: Packages ``neurosync.core`` must not load, not even indirectly (D-01).
HEAVY = {"PyQt5", "PyQt6", "PySide6", "fastapi", "uvicorn", "brainflow", "pylsl", "mne", "scipy"}


def _py_files() -> list[Path]:
    files = sorted(SRC.rglob("*.py"))
    assert files, f"no code found in {SRC}"
    return files


def _calls(tree: ast.AST) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            value = node.func.value
            if isinstance(value, ast.Name):
                out.append((value.id, node.func.attr, node.lineno))
    return out


def test_nobody_reads_wall_clock_except_anchors() -> None:
    bad: list[str] = []
    for path in _py_files():
        if path in WALL_CLOCK_ALLOWED:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for mod, attr, line in _calls(tree):
            if mod == "time" and attr in {"time", "time_ns", "monotonic", "monotonic_ns"}:
                bad.append(f"{path.relative_to(SRC)}:{line} time.{attr}()")
            if mod == "datetime" and attr in {"now", "utcnow", "today"}:
                bad.append(f"{path.relative_to(SRC)}:{line} datetime.{attr}()")
    assert not bad, "use Clock.now_ns() (D-02):\n" + "\n".join(bad)


def test_no_daemon_threads() -> None:
    # D-05: a daemon thread dies without cleanup and can lose data.
    bad: list[str] = []
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "daemon" and isinstance(kw.value, ast.Constant) and kw.value.value:
                        bad.append(f"{path.relative_to(SRC)}:{node.lineno}")
    assert not bad, "daemon threads are forbidden (D-05):\n" + "\n".join(bad)


def test_no_bare_except_and_no_pass_after_except() -> None:
    bad: list[str] = []
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    bad.append(f"{path.relative_to(SRC)}:{node.lineno} bare except")
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    bad.append(f"{path.relative_to(SRC)}:{node.lineno} except with only pass")
    assert not bad, "swallowed errors (D-06):\n" + "\n".join(bad)


def test_importing_core_loads_nothing_heavy() -> None:
    code = (
        "import sys\n"
        "import neurosync.core.anchors, neurosync.core.bus, neurosync.core.clock\n"
        "import neurosync.core.errors, neurosync.core.model, neurosync.core.ring\n"
        f"heavy = {sorted(HEAVY)!r}\n"
        "bad = sorted({m.split('.')[0] for m in sys.modules} & set(heavy))\n"
        "print(','.join(bad))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == "", f"neurosync.core pulls in: {out}"
