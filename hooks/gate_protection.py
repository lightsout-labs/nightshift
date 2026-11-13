#!/usr/bin/env python3
"""PreToolUse hook: only the human approves a gated document.

Blocks an `Edit` or `Write` that would give a file an approved status it does
not have, a shell command that contains the approved status text, and a shell
command that starts a nested `claude` session, where a prompt would count as
human input. Matching shell commands is best effort: it stops mistakes, not a
determined bypass.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import nightshift  # noqa: E402

BLOCK = 2

_APPROVED_TEXT = re.compile(r"status:\s*approved", re.IGNORECASE)
# Where a new command can start inside a shell command line.
_COMMAND_START = re.compile(r"[;&|\n(`]+")
_ASSIGNMENT = re.compile(r"\w+=")
_WRAPPERS = {"env", "exec", "command", "nohup", "time", "sudo", "npx", "bunx"}
_CLAUDE = {"claude", "claude-code"}


def _after_edit(path: Path, tool: str, tool_input: dict) -> str | None:
    """The file's text if the tool call went through, or None if it would
    not change the file."""
    if tool == "Write":
        return tool_input.get("content", "")
    old = tool_input.get("old_string", "")
    new = tool_input.get("new_string", "")
    try:
        text = path.read_text()
    except OSError:
        return None
    if not old or old not in text:
        return None
    count = -1 if tool_input.get("replace_all") else 1
    return text.replace(old, new, count)


def _approves(cwd: Path, tool: str, tool_input: dict) -> bool:
    path = cwd / tool_input.get("file_path", "")
    after = _after_edit(path, tool, tool_input)
    return (
        after is not None
        and nightshift.text_status(after) == nightshift.APPROVED
        and nightshift.document_status(path) != nightshift.APPROVED
    )


def _starts_claude(command: str) -> bool:
    for part in _COMMAND_START.split(command):
        words = part.replace("$", " ").split()
        while words and (_ASSIGNMENT.match(words[0]) or words[0] in _WRAPPERS):
            words.pop(0)
        if words and words[0].rsplit("/", 1)[-1] in _CLAUDE:
            return True
    return False


def decide(event: dict) -> str | None:
    """Return the reason to block the tool call, or None to allow it."""
    cwd = Path(event.get("cwd") or ".")
    if nightshift.find_project(cwd) is None:
        return None
    tool = event.get("tool_name")
    tool_input = event.get("tool_input") or {}
    if tool in ("Edit", "Write"):
        if _approves(cwd, tool, tool_input):
            return (
                "Only the human can approve a gated document. Stop and ask the "
                "human to read it and type `approve`."
            )
    elif tool == "Bash":
        command = tool_input.get("command", "")
        if _APPROVED_TEXT.search(command):
            return (
                "A shell command must not contain the approved status text. Only "
                "the human can approve a gated document, by typing `approve`."
            )
        if _starts_claude(command):
            return (
                "A nested claude session is not allowed in a nightshift project: "
                "a prompt submitted there would count as human input."
            )
    return None


def main() -> int:
    reason = decide(json.load(sys.stdin))
    if reason:
        print(reason, file=sys.stderr)
        return BLOCK
    return 0


if __name__ == "__main__":
    sys.exit(main())
