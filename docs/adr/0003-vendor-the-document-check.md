# 0003: The document check is copied into each project

## Context

`make check` must run the document sync check both locally and in CI. The
plugin is not installed in CI. The options were to install the plugin in CI,
publish the check as a package, or copy it into the project.

## Decision

`build` copies `templates/check-docs.py` to `scripts/check-docs.py` in the
project. It is a single file with no dependencies.

## Consequences

- A project's CI depends only on its own repository.
- Copies can fall behind the plugin. The file carries a version line, and
  `build` replaces an older copy when it starts.
