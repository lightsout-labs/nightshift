---
name: build
description: Build the next slice of a nightshift project. Writes failing tests, then code until make check and make e2e pass, and opens a pull request that merges itself. One slice per run.
disable-model-invocation: true
---

# build: build one slice

Build the first slice of `docs/backlog.md` that is not `Done`, then stop.
Write everything in English. Do the work yourself; do not launch agents. `NS`
below is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/nightshift.py"`, run from the
project root. `Snn` is the slice's number.

## 1. Find the slice

1. Run `NS gate docs/architecture.md docs/backlog.md`. If it fails, tell the
   human what it printed and that `/nightshift:design` comes first, and stop.
2. Run `NS next`. If no slice is left, tell the human: "Every slice is done.
   Run `/clear`, then `/nightshift:release`." Stop.
3. Read `docs/architecture.md`, and only the code the slice touches.
4. `Status: Todo`: create the branch `feat/<short-kebab-title>` from the
   latest `main` and run `NS set-status Snn in-progress`.
   `Status: In progress`: you are resuming. Switch to the slice's branch and
   read its `Notes`, `git log main..`, and `git status`. Carry on from what
   is there, and do not repeat a fix that `Notes` records as failed.

## 2. Tests first

Before any code, write failing tests from the acceptance criteria:

- End to end: the slice's main path and its key failures, not combinations.
- Unit: the core logic, through public interfaces only.
- Every criterion has a test. No test repeats what another already proves.
- Run them. Each must fail because the behavior is missing, not from a typo.

## 3. Code

Write code until `make check` and `make e2e` pass.

- Deep modules: few operations in each interface, substantial behavior
  behind it. Follow the architecture document; if it is wrong, change it in
  this slice. A decision that is costly to reverse gets an ADR from
  `${CLAUDE_PLUGIN_ROOT}/templates/adr.md`.
- Never weaken a test, lower the coverage floor, or switch off a lint rule to
  make a check pass.
- If a criterion is ambiguous in a way that changes behavior, ask the human
  with AskUserQuestion. Decide everything else yourself.
- When a fix fails, add a line to the slice's `Notes`: the problem and what
  you tried. After three failed fixes of the same problem, commit, push,
  tell the human the problem and the three attempts, and stop.
- If `python3 scripts/check-docs.py --version` prints a lower number than
  `${CLAUDE_PLUGIN_ROOT}/templates/check-docs.py --version`, copy it again.

**A walking skeleton slice** also delivers:
- `Makefile`: `check` runs the format check, lint, unit tests with the
  coverage floor, and `python3 scripts/check-docs.py`; `e2e` runs the
  end-to-end tests.
- `scripts/check-docs.py`, copied unchanged from
  `${CLAUDE_PLUGIN_ROOT}/templates/check-docs.py`.
- `CLAUDE.md`, from `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md`, filled in.
- CI that runs on every pull request, with two jobs named exactly `check`
  and `e2e`, and deployment as the architecture document describes.
- With `gh`, after the first push: squash merging only, auto-merge, branch
  deletion on merge, and protection of `main` that requires `check` and
  `e2e`, for administrators too.

## 4. Deliver

1. Update every document the slice affects: architecture, README, ADRs. Add
   to the slice's `Notes` the decisions a later slice needs to know.
2. Commit, push, and open a pull request titled `<type>: <summary> (Snn)`,
   with the body from `${CLAUDE_PLUGIN_ROOT}/templates/pull-request.md`.
3. Run `NS set-status Snn done` and add `PR: #<number>` on the line after
   the status. Run `make check`, commit, push, and run
   `gh pr merge --squash --auto`.
4. Run `gh pr checks --watch`. A failing check is a problem to fix as in
   step 3. When the pull request has merged, switch to the updated `main`.
5. Tell the human what was built in at most five lines, and: "Run `/clear`,
   then `/nightshift:build`." If `NS next` reports that no slice is left,
   name `/nightshift:release` instead. Stop.
