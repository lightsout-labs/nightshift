"""Shared helpers: run scripts and hooks the way skills and Claude Code do."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def run_script(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run `nightshift.py` with `args` from `cwd`."""
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "nightshift.py"), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def run_check_docs(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the document check from `cwd`, as a project's `make check` does."""
    return subprocess.run(
        [sys.executable, str(ROOT / "templates" / "check-docs.py"), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def run_hook(name: str, payload: dict) -> subprocess.CompletedProcess[str]:
    """Run the hook file `hooks/<name>.py` with `payload` as its JSON input."""
    return subprocess.run(
        [sys.executable, str(ROOT / "hooks" / f"{name}.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def write_doc(project: Path, relative: str, status: str | None) -> Path:
    """Write a gated document with the given status line, or none."""
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    status_line = f"Status: {status}\n\n" if status else ""
    path.write_text(f"# Title\n\n{status_line}Body text.\n")
    return path


def git(directory: Path, *args: str) -> str:
    """Run a git command in `directory` and return its output."""
    return subprocess.run(
        ["git", *args], cwd=directory, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """An empty git repository on `main`."""
    git(tmp_path, "init", "--quiet", "--initial-branch=main")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    return tmp_path


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A target project that has adopted the workflow."""
    (tmp_path / ".nightshift").touch()
    (tmp_path / "docs").mkdir()
    return tmp_path
