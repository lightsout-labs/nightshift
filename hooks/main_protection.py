#!/usr/bin/env python3
"""PreToolUse hook: changes reach `main` only through a pull request.

Blocks a shell command that would commit while on `main`, push to `main`, or
force a push. The branch is the one the command would be on when it gets
there, so `git switch -c feat/x && git commit` is allowed on `main`. Matching
shell commands is best effort: it stops mistakes, not a determined bypass.
Server-side branch protection is the real guarantee.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import nightshift  # noqa: E402

BLOCK = 2

COMMIT_ON_MAIN = (
    f"Never commit on `{nightshift.MAIN}`. Create a branch first, in its own "
    "command: `git switch -c <type>/<description>`."
)
PUSH_TO_MAIN = (
    f"Never push to `{nightshift.MAIN}`. Push a branch and open a pull request."
)
FORCE_PUSH = (
    "Force pushes are not allowed in a nightshift project. Add a commit instead "
    "of rewriting pushed history, or ask the human."
)

# Characters that end one simple command and start the next.
_OPERATORS = "();<>|&"
_ASSIGNMENT = re.compile(r"\w+=")
_WRAPPERS = {"env", "exec", "command", "nohup", "time", "sudo"}
_GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
_PUSH_OPTIONS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
_PUSH_EVERY_BRANCH = {"--all", "--branches", "--mirror"}
_CREATE_BRANCH = {"-c", "-C", "--create", "--force-create", "-b", "-B", "--orphan"}
_SHORT_FORCE = re.compile(r"-[A-Za-z]*f[A-Za-z]*")


def _simple_commands(command: str) -> list[list[str]]:
    """Split a shell command line into the words of each simple command.

    Quoted text stays one word, so a commit message never looks like a
    command.
    """
    text = command.replace("\\\n", " ")
    text = text.replace("\n", " ; ").replace("`", " ; ")
    lexer = shlex.shlex(text, posix=True, punctuation_chars=_OPERATORS)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        # Unbalanced quotes, as in a here-document: split without them.
        tokens = re.sub(rf"([{_OPERATORS}]+)", r" \1 ", text).split()
    commands: list[list[str]] = [[]]
    for token in tokens:
        if token and set(token) <= set(_OPERATORS):
            commands.append([])
        else:
            commands[-1].append(token)
    return [words for words in commands if words]


def _git(directory: Path, *args: str) -> str | None:
    """Output of a read-only git command, or None if it fails."""
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), *args], capture_output=True, text=True
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _git_call(words: list[str], directory: Path) -> tuple[Path, list[str]] | None:
    """If the words run git, the directory it runs in and its subcommand with
    arguments."""
    words = list(words)
    while words and (_ASSIGNMENT.match(words[0]) or words[0] in _WRAPPERS):
        words.pop(0)
    if not words or words.pop(0).rsplit("/", 1)[-1] != "git":
        return None
    while words and words[0].startswith("-"):
        option = words.pop(0)
        if option in _GIT_OPTIONS_WITH_VALUE and words:
            value = words.pop(0)
            if option == "-C":
                directory = directory / value
    return (directory, words) if words else None


def _switch_target(directory: Path, args: list[str]) -> str | None:
    """The branch that `git switch` or `git checkout` moves to, when that is
    certain."""
    create = False
    for arg in args:
        if arg == "--":
            break
        if arg in _CREATE_BRANCH:
            create = True
        elif not arg.startswith("-"):
            exists = _git(directory, "rev-parse", "--verify", f"refs/heads/{arg}")
            return arg if create or exists else None
    return None


def _push_reason(args: list[str], branch: str | None) -> str | None:
    positional: list[str] = []
    tags_only = False
    remaining = iter(args)
    for arg in remaining:
        if arg == "--":
            positional.extend(remaining)
        elif arg in _PUSH_OPTIONS_WITH_VALUE:
            next(remaining, None)
        elif arg.startswith("--force") or _SHORT_FORCE.fullmatch(arg):
            return FORCE_PUSH
        elif arg in _PUSH_EVERY_BRANCH:
            return PUSH_TO_MAIN
        elif arg == "--tags":
            tags_only = True
        elif not arg.startswith("-"):
            positional.append(arg)
    refspecs = positional[1:]
    if any(refspec.startswith("+") for refspec in refspecs):
        return FORCE_PUSH
    # Without a refspec, git pushes the current branch.
    targets = [] if tags_only and not refspecs else refspecs or ["HEAD"]
    for refspec in targets:
        target = refspec.rpartition(":")[2]
        if target in ("HEAD", "@"):
            target = branch or ""
        if target.removeprefix("refs/heads/") == nightshift.MAIN:
            return PUSH_TO_MAIN
    return None


def decide(event: dict) -> str | None:
    """Return the reason to block the tool call, or None to allow it."""
    directory = Path(event.get("cwd") or ".")
    if event.get("tool_name") != "Bash" or nightshift.find_project(directory) is None:
        return None
    # The branch an earlier `git switch` in the same command line moves to.
    switched = None
    for words in _simple_commands((event.get("tool_input") or {}).get("command", "")):
        if words[0] == "cd" and len(words) == 2:
            directory, switched = directory / words[1], None
            continue
        call = _git_call(words, directory)
        if call is None:
            continue
        repository, (subcommand, *args) = call
        branch = switched or _git(repository, "symbolic-ref", "--short", "HEAD")
        if subcommand in ("switch", "checkout"):
            switched = _switch_target(repository, args) or switched
        elif subcommand == "commit" and branch == nightshift.MAIN:
            return COMMIT_ON_MAIN
        elif subcommand == "push":
            reason = _push_reason(args, branch)
            if reason:
                return reason
    return None


def main() -> int:
    reason = decide(json.load(sys.stdin))
    if reason:
        print(reason, file=sys.stderr)
        return BLOCK
    return 0


if __name__ == "__main__":
    sys.exit(main())
