# 0002: One backlog file is the only progress state

## Context

A slice must be able to start from a fresh context, and hooks must know
whether `build` is running. The options were one Markdown file, one file per
slice with an index, or a machine-readable state file beside the documents.

## Decision

Keep every slice, its status, and its notes in `docs/backlog.md`. Scripts and
hooks parse that file. There is no other state.

## Consequences

- One file to read, review, and keep in sync; nothing can disagree with it.
- The format is a contract. `check-docs.py` rejects a malformed backlog.
- The file grows with the project. At about ten lines per slice this is
  acceptable; the `next` subcommand prints one section so that skills do not
  read the whole file.
