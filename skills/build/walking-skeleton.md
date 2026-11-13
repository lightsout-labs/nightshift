# What a walking skeleton slice also delivers

`PLUGIN` is the plugin's root, as in the `build` skill.

- `Makefile`: `check` runs the format check, lint, unit tests with the
  coverage floor, and `python3 scripts/check-docs.py`; `e2e` runs the
  end-to-end tests.
- `scripts/check-docs.py`, copied unchanged from
  `PLUGIN/templates/check-docs.py`.
- `CLAUDE.md`, from `PLUGIN/templates/CLAUDE.md`, filled in.
- `README.md`, which `spec` started: add how to install, run, and test the
  project, and where it is deployed.
- CI that runs on every pull request, with two jobs named exactly `check`
  and `e2e`, and deployment as the architecture document describes.
- With `gh`, after the first push: squash merging only, auto-merge, branch
  deletion on merge, and protection of `main` that requires `check` and
  `e2e`, for administrators too.
