#!/usr/bin/env python3
"""Check that a project's documents are consistent with each other.

Run from the project root, as part of `make check`. Exits 1 and names each
file and reason when:

- a gated document has no valid `Status` line;
- a backlog section is malformed, or more than one slice is `In progress`;
- a `Done` slice has no pull request number;
- a relative link in `docs/` points to a file that does not exist.

This file is copied from the nightshift plugin and replaced when the plugin
has a newer version. Do not edit the copy.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

VERSION = 1

DOCS = Path("docs")
BACKLOG = DOCS / "backlog.md"
GATED = ("requirements.md", "architecture.md", "backlog.md", "delivery/*.md")

_DOCUMENT_STATUS = re.compile(r"Status: (Draft|Approved)")
_SLICE_HEADING = re.compile(r"## (S\d+): .+")
_SLICE_STATUS = re.compile(r"Status: (Todo|In progress|Done)")
_PULL_REQUEST = re.compile(r"PR: #\d+")
_FENCE = re.compile(r"\s*(```|~~~)")
_INLINE_CODE = re.compile(r"`[^`]*`")
_LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")


def _first_line_after(lines: list[str], index: int, end: int) -> str:
    """The first line that is not blank in `lines[index + 1 : end]`."""
    return next((line for line in lines[index + 1 : end] if line.strip()), "")


def _status_problems(lines: list[str]) -> list[str]:
    title = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if title is not None and _DOCUMENT_STATUS.fullmatch(
        _first_line_after(lines, title, len(lines))
    ):
        return []
    return ["no valid Status line (Status: Draft | Approved) after the title"]


def _backlog_problems(lines: list[str]) -> list[str]:
    problems = []
    seen: list[str] = []
    in_progress = []
    headings = [i for i, line in enumerate(lines) if line.startswith("## ")]
    for start, end in zip(headings, [*headings[1:], len(lines)]):
        heading = _SLICE_HEADING.fullmatch(lines[start])
        if not heading:
            title = lines[start][3:].strip()
            problems.append(f'section "{title}" has no slice heading (## Snn: title)')
            continue
        slice_id = heading[1]
        if slice_id in seen:
            problems.append(f"{slice_id} appears more than once")
        seen.append(slice_id)

        section = lines[start + 1 : end]
        criteria = next(
            (i for i, line in enumerate(section) if line == "Acceptance criteria:"),
            None,
        )
        if criteria is None or not _first_line_after(
            section, criteria, len(section)
        ).startswith("- "):
            problems.append(f"{slice_id} has no acceptance criteria")

        status = _SLICE_STATUS.fullmatch(_first_line_after(lines, start, end))
        if not status:
            problems.append(
                f"{slice_id} has no valid status line"
                " (Status: Todo | In progress | Done) after its heading"
            )
        elif status[1] == "In progress":
            in_progress.append(slice_id)
        elif status[1] == "Done" and not any(
            _PULL_REQUEST.fullmatch(line) for line in section
        ):
            problems.append(
                f"{slice_id} is Done but has no pull request number (PR: #n)"
            )
    if len(in_progress) > 1:
        problems.append(
            f"{' and '.join(in_progress)} are In progress; only one slice can be"
        )
    return problems


def _link_problems(path: Path, lines: list[str]) -> list[tuple[int, str]]:
    """Broken relative links, as (line number, reason). Code is not read."""
    problems = []
    fence = None
    for number, line in enumerate(lines, start=1):
        marker = _FENCE.match(line)
        if marker and fence in (None, marker[1]):
            fence = None if fence else marker[1]
            continue
        if fence:
            continue
        for link in _LINK.finditer(_INLINE_CODE.sub("", line)):
            target = link[1]
            if _SCHEME.match(target) or target.startswith(("#", "/")):
                continue
            relative = unquote(re.split(r"[#?]", target)[0])
            if not (path.parent / relative).exists():
                problems.append((number, f"broken link to {target}"))
    return problems


def check() -> list[str]:
    """Return every problem in the documents under `docs/`, one per line."""
    if not DOCS.is_dir():
        return [f"{DOCS}/: not found; run this from the project root"]
    gated = {path for pattern in GATED for path in DOCS.glob(pattern)}
    problems = []
    for path in sorted(DOCS.rglob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        name = path.as_posix()
        found = _status_problems(lines) if path in gated else []
        if path == BACKLOG:
            found += _backlog_problems(lines)
        problems += [f"{name}: {problem}" for problem in found]
        problems += [
            f"{name}:{number}: {problem}"
            for number, problem in _link_problems(path, lines)
        ]
    return problems


def main(argv: list[str]) -> int:
    if argv == ["--version"]:
        print(VERSION)
        return 0
    if argv:
        print("usage: check-docs.py [--version]", file=sys.stderr)
        return 2
    problems = check()
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
