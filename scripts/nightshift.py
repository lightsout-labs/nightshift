#!/usr/bin/env python3
"""Deterministic helpers for the nightshift workflow.

Skills run this file as a command so that they never spend tokens on what can
be computed. Hooks import it, so that the target project contract (marker
file, gated documents, status line, backlog format) is written down in one
place.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
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

BACKLOG = "docs/backlog.md"
ARCHIVE = "docs/backlog"
TODO = "Todo"
IN_PROGRESS = "In progress"
DONE = "Done"
SLICE_STATUSES = (TODO, IN_PROGRESS, DONE)

_STATUS_LINE = re.compile(rf"Status: ({DRAFT}|{APPROVED})")
_SLICE_HEADING = re.compile(r"## (S\d+): .+")
_SLICE_STATUS_LINE = re.compile(rf"Status: ({'|'.join(SLICE_STATUSES)})")
_VERSION = re.compile(r"v\d+\.\d+\.\d+")


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


class BacklogError(Exception):
    """The backlog is missing, malformed, or does not allow the change."""


@dataclass
class Slice:
    """One section of the backlog, as line positions in the file."""

    id: str
    status: str
    start: int
    end: int
    status_index: int


def backlog_slices(lines: list[str]) -> list[Slice]:
    """Return the slices of a backlog in document order.

    A slice runs from its `## Snn: title` heading to the next second-level
    heading. Its status is the first line after the heading.
    """
    slices = []
    headings = [i for i, line in enumerate(lines) if line.startswith("## ")]
    for start, end in zip(headings, [*headings[1:], len(lines)]):
        heading = _SLICE_HEADING.fullmatch(lines[start])
        if not heading:
            continue
        index = next((i for i in range(start + 1, end) if lines[i].strip()), None)
        status = index is not None and _SLICE_STATUS_LINE.fullmatch(lines[index])
        if not status:
            raise BacklogError(f"{heading[1]} has no valid status line")
        slices.append(Slice(heading[1], status[1], start, end, index))
    return slices


def _read_backlog() -> list[str]:
    try:
        return Path(BACKLOG).read_text().splitlines(keepends=True)
    except OSError:
        raise BacklogError("not found; run this from the project root") from None


def _next() -> int:
    lines = [line.rstrip("\r\n") for line in _read_backlog()]
    slices = backlog_slices(lines)
    for item in slices:
        if item.status != DONE:
            print("\n".join(lines[item.start : item.end]).rstrip())
            return 0
    if slices:
        print("No slice is left: every slice is Done.")
    else:
        print("The backlog has no slices: nothing is planned or left to release.")
    return 0


def _set_status(slice_id: str, status: str) -> int:
    lines = _read_backlog()
    slices = backlog_slices([line.rstrip("\r\n") for line in lines])
    target = next((item for item in slices if item.id == slice_id), None)
    if target is None:
        raise BacklogError(f"there is no slice {slice_id}")
    running = [s.id for s in slices if s.status == IN_PROGRESS and s is not target]
    if status == IN_PROGRESS and running:
        raise BacklogError(
            f"{running[0]} is already In progress; only one slice can be"
        )
    old = lines[target.status_index]
    lines[target.status_index] = f"Status: {status}" + old[len(old.rstrip("\r\n")) :]
    Path(BACKLOG).write_text("".join(lines))
    return 0


def _archive(version: str) -> int:
    """Move the slices of a finished release out of the backlog."""
    lines = _read_backlog()
    slices = backlog_slices([line.rstrip("\r\n") for line in lines])
    if not slices:
        raise BacklogError("has no slices to archive")
    open_slices = [item.id for item in slices if item.status != DONE]
    if open_slices:
        raise BacklogError(f"not Done: {', '.join(open_slices)}")
    archive = Path(ARCHIVE) / f"{version}.md"
    if archive.exists():
        raise BacklogError(f"{archive.as_posix()} already exists")
    first = slices[0].start
    archive.parent.mkdir(exist_ok=True)
    archive.write_text(
        f"# Backlog of {version}\n\n"
        f"The slices delivered in {version}, moved here from"
        " [backlog.md](../backlog.md).\n\n" + "".join(lines[first:])
    )
    Path(BACKLOG).write_text("".join(lines[:first]).rstrip() + "\n")
    print(f"Moved {len(slices)} slices to {archive.as_posix()}")
    return 0


def _version(text: str) -> str:
    if not _VERSION.fullmatch(text):
        raise argparse.ArgumentTypeError(f"{text!r} is not vMAJOR.MINOR.PATCH")
    return text


def _slice_status(text: str) -> str:
    """Accept a slice status in any case, with a hyphen for the space."""
    wanted = text.replace("-", " ").lower()
    for status in SLICE_STATUSES:
        if status.lower() == wanted:
            return status
    names = ", ".join(SLICE_STATUSES)
    raise argparse.ArgumentTypeError(f"{text!r} is not one of: {names}")


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
    commands.add_parser(
        "next", help="print the section of the first slice that is not Done"
    )
    set_status = commands.add_parser(
        "set-status", help="change one slice's status in the backlog"
    )
    set_status.add_argument("slice", help="slice number, such as S03")
    set_status.add_argument(
        "status", type=_slice_status, help=" | ".join(SLICE_STATUSES)
    )
    archive = commands.add_parser(
        "archive", help="move the slices, all Done, to docs/backlog/<version>.md"
    )
    archive.add_argument("version", type=_version, help="such as v1.2.0")
    args = parser.parse_args(argv)
    try:
        if args.command == "gate":
            return _gate(args.documents)
        if args.command == "next":
            return _next()
        if args.command == "archive":
            return _archive(args.version)
        return _set_status(args.slice, args.status)
    except BacklogError as error:
        print(f"{BACKLOG}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
