# What a walking skeleton slice also delivers

`PLUGIN` is the plugin's root and `NS` the script, as in the `build`
skill.

- `Makefile`: `check` runs the format check, lint, unit tests with the
  coverage floor, and `python3 scripts/check-docs.py`; `e2e` runs the
  end-to-end tests.
- `scripts/check-docs.py`, copied unchanged from
  `PLUGIN/templates/check-docs.py`.
- `CLAUDE.md`, from `PLUGIN/templates/CLAUDE.md`, filled in.
- `README.md`, which `spec` started: add how to install, run, and test the
  project, and where it is deployed.
- With `ci: yes` in `NS config`: CI that runs on every pull request, with
  two jobs named exactly `check` and `e2e`. With `ci: no`: no CI.
- Deployment as the architecture document describes.
- With `gh`, after the first push: squash merging only, branch deletion on
  merge, and protection of `main` against direct and force pushes, for
  administrators too. With `ci: yes`, also auto-merge, and the protection
  requires `check` and `e2e`.
