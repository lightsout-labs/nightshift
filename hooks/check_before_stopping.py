#!/usr/bin/env python3
"""Stop hook: the agent cannot stop a slice while `make check` fails.

While a slice is `In progress`, the hook runs `make check` and blocks the
stop when it fails, passing the output to the agent. The third failure in a
row does not block: the agent is told to ask the human, and its next stop
goes through. The check is skipped while the working tree is the one that
last passed. State is kept in the git directory, so it is never committed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import nightshift  # noqa: E402

BLOCK = 2
LIMIT = 3
# The end of the output is where a failing check names what failed.
OUTPUT_CHARACTERS = 6000

FIX = "`make check` fails (failure {count} of {limit} in a row). Fix it, then stop."
ASK = (
    f"`make check` has failed {LIMIT} times in a row. Do not try another fix. "
    "Tell the human the problem and what you tried, ask how to go on, and stop."
)


def _building(project: Path) -> bool:
    """Whether a slice is `In progress`, which is how `build` shows it runs."""
    try:
        lines = (project / nightshift.BACKLOG).read_text().splitlines()
        slices = nightshift.backlog_slices(lines)
    except (OSError, nightshift.BacklogError):
        return False
    return any(item.status == nightshift.IN_PROGRESS for item in slices)


def _git(project: Path, *args: str, env: dict | None = None) -> str | None:
    """Output of a git command in the project, or None if it fails."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project), *args], capture_output=True, text=True, env=env
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


class State:
    """What the hook remembers between stops, in `.git/nightshift/`."""

    def __init__(self, project: Path, directory: Path):
        self.project = project
        self.directory = directory
        self.file = directory / "stop.json"
        try:
            saved = json.loads(self.file.read_text())
        except (OSError, ValueError):
            saved = {}
        self.failures: int = saved.get("failures", 0)
        self.passed: str | None = saved.get("passed")

    def save(self) -> None:
        self.file.write_text(
            json.dumps({"failures": self.failures, "passed": self.passed})
        )

    def working_tree(self) -> str | None:
        """A hash of every file git does not ignore, committed or not.

        The files are staged in an index of the hook's own, so the project's
        index and `git status` are untouched.
        """
        env = {**os.environ, "GIT_INDEX_FILE": str(self.directory / "index")}
        if _git(self.project, "add", "--all", env=env) is None:
            return None
        # Blobs staged at an earlier stop may have been pruned since.
        return _git(self.project, "write-tree", "--missing-ok", env=env)


def _open_state(project: Path) -> State | None:
    path = _git(project, "rev-parse", "--git-path", "nightshift")
    if path is None:
        return None
    directory = (project / path).resolve()
    directory.mkdir(exist_ok=True)
    return State(project, directory)


def _make_check(project: Path) -> tuple[bool, str]:
    """Run `make check`; return whether it passed and the end of its output."""
    try:
        result = subprocess.run(
            ["make", "check"],
            cwd=project,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
    except OSError as error:
        return False, f"make could not be run: {error}"
    return result.returncode == 0, result.stdout[-OUTPUT_CHARACTERS:].strip()


def main() -> int:
    event = json.load(sys.stdin)
    project = nightshift.find_project(event.get("cwd") or ".")
    if project is None or not _building(project):
        return 0
    state = _open_state(project)
    if state is None:
        return 0
    if state.failures >= LIMIT:
        # The agent was sent to the human at the last stop: let it ask.
        state.failures = 0
        state.save()
        return 0
    tree = state.working_tree()
    if tree is not None and tree == state.passed:
        return 0
    passed, output = _make_check(project)
    if passed:
        # Hashed again, because the check itself may have written files.
        state.failures, state.passed = 0, state.working_tree()
        state.save()
        return 0
    state.failures += 1
    state.save()
    if state.failures < LIMIT:
        print(FIX.format(count=state.failures, limit=LIMIT), file=sys.stderr)
        print(f"\n{output}", file=sys.stderr)
        return BLOCK
    feedback = {"hookEventName": "Stop", "additionalContext": f"{ASK}\n\n{output}"}
    print(json.dumps({"hookSpecificOutput": feedback}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
