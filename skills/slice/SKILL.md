---
name: slice
description: Split a nightshift project's design into docs/backlog.md, a walking skeleton followed by vertical slices with acceptance criteria. Run by design, or alone to revise the backlog.
disable-model-invocation: true
---

# slice: split the design into a backlog

Write `docs/backlog.md` in English. Do the work yourself; do not launch
agents. `NS` below is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/nightshift.py"`,
run from the project root.

## 1. Check the gate (only when run alone)

Run `NS gate docs/requirements.md`. If it fails, or `docs/architecture.md`
does not exist, tell the human that `/nightshift:spec` and
`/nightshift:design` come first, and stop. Otherwise create the branch
`docs/backlog` from the latest `main`.

## 2. Write

Copy `${CLAUDE_PLUGIN_ROOT}/templates/backlog.md` to `docs/backlog.md` and
replace its slices with the real ones. If a backlog exists, revise it instead:
leave `Done` slices as they are and set the document to `Status: Draft`.

- **S01 is a walking skeleton**: the thinnest path through every part of the
  architecture, doing one trivial thing end to end. It also delivers the
  `Makefile` with `check` and `e2e`, CI with both as required checks, branch
  protection, and deployment.
- **Every other slice is vertical**: one behavior the user can see, through
  every layer it needs, with its own end-to-end test. Never a slice for one
  layer, for "setup", or for tests alone.
- **Small**: a slice is built in one session from a fresh context. Split a
  slice that needs more than about seven acceptance criteria.
- **Ordered**: a slice depends only on earlier slices. Put the riskiest and
  the most valuable behavior early.
- **Acceptance criteria** are observable statements that each become a test.
  Say what happens, not how it is built. End each with the requirement it
  serves, such as `(R3)`.
- Every requirement is served by at least one slice. Nothing in the backlog
  goes beyond the requirements.
- Keep the format exact, because scripts parse it: `## Snn: <title>`, a blank
  line, `Status: Todo`, a blank line, `Acceptance criteria:` and its list.
  Add no `PR` or `Notes`; `build` writes those.

## 3. Check

Run `NS next`. It must print the first slice that is not `Done`; fix the
format if it reports an error. Then read the backlog once against the
requirements and fix any requirement that no slice serves.

If `design` sent you here, return to it now.

## 4. Open the gate (only when run alone)

Commit with the message `docs: revise backlog`, push, and open a pull request
with the same title. Print the path, the list of slice titles, and: "Read
`docs/backlog.md`. Reply with changes, or type `approve`." Stop. You cannot
approve it yourself. On changes, apply them, push, and stop again. On
`approve`, commit the status change, push, squash-merge, and tell the human to
run `/clear` and then `/nightshift:build`.
