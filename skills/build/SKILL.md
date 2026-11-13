---
name: build
description: Build the next slice of a nightshift project. Writes failing tests, then code until make check and make e2e pass, and opens a pull request that merges itself. One slice per run.
disable-model-invocation: true
---

# build: build one slice

Build the first slice of `docs/backlog.md` that is not `Done`, then stop.
Write everything in English. Do the work yourself; the only agent you launch
is the reviewer in step 4. `PLUGIN` below is `${CLAUDE_PLUGIN_ROOT}`, `NS` is
`python3 "PLUGIN/scripts/nightshift.py"` run from the project root, and `Snn`
is the slice's number.

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

Write code until `make check` and `make e2e` pass. Keep it simple in scope,
not in quality: nothing for a later slice or a need no criterion states.

- Deep modules: few operations in each interface, substantial behavior
  behind it. Follow the architecture document; if it is wrong, change it in
  this slice. A decision that is costly to reverse gets an ADR from
  `PLUGIN/templates/adr.md`.
- Never weaken a test, the coverage floor, or a lint rule to pass a check.
- If a criterion is ambiguous in a way that changes behavior, ask the human
  with AskUserQuestion. Decide everything else yourself.
- When a fix fails, add a line to the slice's `Notes`: the problem and what
  you tried. After three failed fixes of the same problem, commit, push,
  tell the human the problem and the three attempts, and stop.
- If `python3 scripts/check-docs.py --version` prints a lower number than
  `PLUGIN/templates/check-docs.py --version`, copy it again.
- Walking skeleton slice only: read `PLUGIN/skills/build/walking-skeleton.md`.

## 4. Review

Once per slice. If `.git/nightshift/review-Snn.md` exists, go to 3.

1. Update every document the slice affects: architecture, README, ADRs. Run
   `make check` and commit. Run `mkdir -p .git/nightshift`, then
   `git diff main...HEAD > .git/nightshift/review.diff` and
   `NS next > .git/nightshift/slice.md`.
2. Launch the `nightshift:slice-reviewer` agent with the prompt "Review the
   slice." and no word more. Save its reply as `.git/nightshift/review-Snn.md`.
3. Fix every blocking finding in that file, and each minor one that is
   right, as in step 3. Do not review again.

## 5. Deliver

1. Add to the slice's `Notes` the decisions a later slice needs to know.
   Commit, push, and open a pull request titled `<type>: <summary> (Snn)`,
   with the body from `PLUGIN/templates/pull-request.md`.
2. Run `NS set-status Snn done`, add `PR: #<number>` on the line after the
   status, run `make check`, commit, push, and `gh pr merge --squash --auto`.
3. Run `gh pr checks --watch`. A failing check is a problem to fix as in
   step 3. When the pull request has merged, switch to the updated `main`.
4. Tell the human what was built in at most five lines, and: "Run `/clear`,
   then `/nightshift:build`." If `NS next` reports that no slice is left,
   name `/nightshift:release` instead. Stop.
