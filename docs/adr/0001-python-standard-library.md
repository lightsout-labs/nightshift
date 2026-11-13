# 0001: Hooks and scripts use the Python standard library

## Context

Hooks receive JSON on standard input and must parse Markdown and git state.
They run on the user's machine on every tool call, and `check-docs.py` also
runs in each target project's CI. The options were POSIX shell with `jq`,
Node.js, or Python.

## Decision

Write hooks and scripts in Python 3 with no third-party packages.

## Consequences

- No install step. Python 3 is present on macOS, Linux, and GitHub's CI
  runners.
- JSON and text handling are testable with ordinary unit tests, unlike shell.
- Windows users need Python on the path. This is accepted for now.
- Each hook pays Python's start-up time on every tool call, measured at about
  20 ms on the development machine.
