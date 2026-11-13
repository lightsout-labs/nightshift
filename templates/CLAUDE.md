# <project>

<One sentence: what the project is.> It is built with the `nightshift`
workflow. What it must do is in `docs/requirements.md`, how it is built is in
`docs/architecture.md`, and progress is in `docs/backlog.md`.

## Commands

- `make check`: <format check, lint, unit tests, coverage floor, document
  check>. Run it after every change.
- `make e2e`: <end-to-end tests>. Run it before a pull request.
- <How to run the project locally.>

## Rules

- Work on one slice at a time, with `/nightshift:build`. Tests come first.
- Tests go through public interfaces only.
- Never commit to `main`. One branch and one squash-merged pull request per
  slice.
- Code, comments, documents, and commit messages are in English.
- Update the affected documents in the same change as the behavior.
- Do not edit `scripts/check-docs.py`; it is a copy from the plugin.
