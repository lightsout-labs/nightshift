---
name: design
description: Design a nightshift project. Writes docs/architecture.md, ADRs, and a backlog of vertical slices as drafts, and stops for the human's approval.
disable-model-invocation: true
---

# design: decide how to build it

Turn the approved requirements into `docs/architecture.md`, ADRs, and
`docs/backlog.md`, and stop at the design gate. Write everything in English.
Do the work yourself; do not launch agents.

## 1. Check the gate

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/nightshift.py" gate docs/requirements.md`
from the project root. If it fails, tell the human what it printed and that
`/nightshift:spec` comes first, and stop.

## 2. Decide

Read `docs/requirements.md`, the existing code if there is any, and an
existing `docs/architecture.md` (then you are revising it). Ask the human,
with AskUserQuestion, only where a requirement is ambiguous in a way that
changes the design. Decide everything else yourself:

- The simplest stack that meets the requirements and constraints.
- Deep modules: few operations in each interface, substantial behavior
  behind it. If a module only passes calls through, merge it into another.
- How each level is tested, the coverage floor, and how the project deploys.
- `make check` and `make e2e` are fixed: the workflow runs them by name.

## 3. Write

1. Create the branch `docs/design` from the latest `main`.
2. Copy `${CLAUDE_PLUGIN_ROOT}/templates/architecture.md` to
   `docs/architecture.md` and fill in every section. Keep `Status: Draft`.
3. For each decision that is costly to reverse, copy
   `${CLAUDE_PLUGIN_ROOT}/templates/adr.md` to `docs/adr/NNNN-<title>.md`,
   numbered from `0001`, and link it from the architecture document. Other
   decisions need one line of reasoning in the document, not an ADR.
4. Read `${CLAUDE_PLUGIN_ROOT}/skills/slice/SKILL.md` and follow its steps 2
   and 3 to write `docs/backlog.md`. Then come back here.

## 4. Open the gate

1. Commit the documents with the message `docs: draft design`, push, and open
   a pull request with the same title. If there is no remote or `gh` fails,
   say so and carry on without one.
2. Print the paths of the architecture document and the backlog, a summary of
   at most five lines for each, and: "Read both documents. Reply with
   changes, or type `approve`."
3. Stop.

You cannot approve the documents yourself, and a hook blocks the attempt.

## 5. After the human replies

- **Changes**: apply them to every document they affect, commit, push, print
  what changed, and stop again.
- **`approve`**: a hook sets both statuses and tells you. Commit the change
  with the message `docs: approve design`, push, squash-merge the pull
  request, and switch to the updated `main`. With no pull request,
  fast-forward `main` to the branch instead. Then tell the human: "The design
  is approved. Run `/clear`, then `/nightshift:build` to build the first
  slice." Stop.
