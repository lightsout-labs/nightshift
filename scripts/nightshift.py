#!/usr/bin/env python3
"""Deterministic helpers for the nightshift workflow.

Skills run this file as a command so that they never spend tokens on what can
be computed. Hooks import it, so that the target project contract (marker
file, gated documents, status line) is written down in one place.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MARKER = ".nightshift"
MAIN = "main"
GATED = (
    "docs/requirements.md",
    "docs/architecture.md",
    "docs/backlog.md",
    "docs/delivery/*.md",
)
DRAFT = "Draft"
APPROVED = "Approved"

_STATUS_LINE = re.compile(rf"Status: ({DRAFT}|{APPROVED})")


def find_project(start: str | Path) -> Path | None:
    """Return the root of the project that contains `start`, if it has adopted
    the workflow."""
    start = Path(start).resolve()
    for directory in (start, *start.parents):
        if (directory / MARKER).is_file():
            return directory
    return None


def _status_index(lines: list[str]) -> int | None:
    """Index of the document's status line: the first line after the title."""
    title = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if title is None:
        return None
    for index in range(title + 1, len(lines)):
        if lines[index].strip():
            return index if _STATUS_LINE.fullmatch(lines[index]) else None
    return None


def text_status(text: str) -> str | None:
    """Return `Draft` or `Approved` for a document's text, or None if it has
    no valid status line."""
    lines = text.splitlines()
    index = _status_index(lines)
    return None if index is None else lines[index].removeprefix("Status: ")


def document_status(path: Path) -> str | None:
    """Like `text_status`, for a file. A missing file has no status."""
    try:
        return text_status(path.read_text())
    except OSError:
        return None


def approve_drafts(project: Path) -> list[str]:
    """Set every gated document that is `Draft` to `Approved`.

    Returns the paths that changed, relative to the project root.
    """
    approved = []
    for pattern in GATED:
        for path in sorted(project.glob(pattern)):
            lines = path.read_text().splitlines(keepends=True)
            index = _status_index([line.rstrip("\r\n") for line in lines])
            if index is None or DRAFT not in lines[index]:
                continue
            lines[index] = lines[index].replace(DRAFT, APPROVED)
            path.write_text("".join(lines))
            approved.append(path.relative_to(project).as_posix())
    return approved


def _gate(documents: list[str]) -> int:
    closed = []
    for document in documents:
        path = Path(document)
        status = document_status(path)
        if status == APPROVED:
            continue
        reason = status or ("no status" if path.is_file() else "missing")
        closed.append(f"{document} ({reason})")
    if closed:
        print("Gate closed. Not approved: " + ", ".join(closed), file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nightshift.py", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    gate = commands.add_parser(
        "gate", help="exit 0 only if every named document is Approved"
    )
    gate.add_argument("documents", nargs="+", metavar="doc")
    args = parser.parse_args(argv)
    return _gate(args.documents)


if __name__ == "__main__":
    sys.exit(main())
