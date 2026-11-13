# Architecture

Status: Approved

This document describes how the `nightshift` plugin is built. What it must do
is in [requirements.md](requirements.md). Rationale for the decisions that are
costly to reverse is in [adr/](adr/).

## Overview

`nightshift` has three kinds of parts, split by who decides:

| Part | Decides | Form |
|---|---|---|
| Skills | What needs judgment: questions, design, code | Prompts, one per stage |
| Scripts | What can be computed: gates, document sync, next slice | Python, run by skills and by `make check` |
| Hooks | What must never happen | Python, run by Claude Code on tool calls |

A target project holds all workflow state in Markdown files under `docs/`.
The plugin holds no state of its own, so any stage can start from a fresh
context.

## Repository layout

```
.claude-plugin/
  plugin.json          Plugin manifest
  marketplace.json     Marketplace with one entry, source "./"
skills/
  spec/SKILL.md        One directory per stage: spec, design, slice,
  ...                  build, release
agents/
  slice-reviewer.md    The only agent the plugin defines: the per-slice review
hooks/
  hooks.json           Hook registration
  *.py                 One file per hook
scripts/
  nightshift.py        Deterministic helpers used by skills (see below)
templates/             Files copied into target projects
tests/                 Tests for hooks, scripts, and plugin structure
Makefile               `make check` and `make e2e` for this repository
pyproject.toml         Development tools and their settings; nothing is packaged
.github/workflows/     CI: the `check` and `e2e` jobs
docs/                  Requirements, this document, ADRs, backlog
```

Skills are invoked as `/nightshift:spec`, `/nightshift:design`, and so on.

## Target project contract

Everything the plugin knows about a project is in this section. Skills, hooks,
and scripts depend on nothing else.

### Files

| Path | Written by | Gated |
|---|---|---|
| `.nightshift` | `spec` | No. Empty marker file; hooks do nothing without it |
| `docs/requirements.md` | `spec` | Yes |
| `docs/architecture.md` | `design` | Yes |
| `docs/adr/NNNN-<title>.md` | `design`, `build` | No |
| `docs/backlog.md` | `slice`, updated by `build` | Yes |
| `docs/delivery/vX.Y.Z.md` | `release` | Yes; approval is the acceptance |
| `scripts/check-docs.py` | `build`, in the walking skeleton | No |

A gated document has `Status: Draft` or `Status: Approved` as the first line
after its title. The human approves by typing `approve` in Claude Code (see
[Gates](#gates)). The architecture document and the backlog are approved
together at the design gate.

### Backlog format

`docs/backlog.md` is the only record of progress. Each slice is one section:

```markdown
## S03: Edit a cell and see dependent cells update

Status: Todo | In progress | Done
PR: #12

Acceptance criteria:
- ...

Notes:
- ...
```

- Slices are built in document order. The next slice is the first one that is
  not `Done`.
- At most one slice is `In progress`. This is also how the hooks know that
  `build` is running.
- `Notes` holds what a fresh context needs to resume: decisions made in the
  slice and failed fix attempts.
- `PR` and `Notes` are added when there is something to record.

### Make targets

| Target | Contents | Runs |
|---|---|---|
| `make check` | Format check, lint, unit tests, coverage floor, `scripts/check-docs.py` | On every change, in the stop hook, in CI |
| `make e2e` | End-to-end tests | Before a slice's pull request, in CI |

CI must expose these as two required checks named `check` and `e2e`. How a
project deploys is described in its own architecture document, because it
depends on the toolchain.

## Skills

Every skill starts by running the gate script for its inputs and stops with a
message to the human if a gate is closed.

| Skill | Requires | Does | Ends |
|---|---|---|---|
| `spec` | Nothing | Asks clarifying questions until no requirement is ambiguous, then writes `docs/requirements.md` from the template | Stops at the requirements gate |
| `design` | Requirements approved | Writes `docs/architecture.md` and ADRs, then runs `slice` | Stops at the design gate |
| `slice` | Requirements approved, architecture exists | Writes `docs/backlog.md`: a walking skeleton first, then vertical slices with acceptance criteria | Returns to `design`, or stops if run alone |
| `build` | Architecture and backlog approved | Builds the next slice (see below) | Stops after one slice |
| `release` | All slices `Done` | Tags a version, writes the changelog, deploys, writes the delivery report | Stops at the acceptance gate |

### Gates

A gate costs the human one word. When a stage reaches a gate, the skill:

1. Commits the draft, opens a pull request, and prints the paths of the
   documents to read with a short summary of each.
2. Stops. The human either replies with changes, which the skill applies
   before stopping again, or types `approve`.
3. On `approve`, the approval hook sets the status and tells the agent, which
   commits the change, merges the pull request, and carries on without
   another command:

| Gate | After `approve` |
|---|---|
| Requirements | Starts `design` in the same session; the clarifying answers are useful context for it |
| Design | Stops and asks for `/clear` and `/nightshift:build`, so the first slice starts clean |
| Acceptance | Closes the release; nothing follows |

The human never needs to open GitHub or edit a file. Editing the `Status`
line by hand has the same effect and remains possible.

### Building a slice

Each run of `/nightshift:build` builds one slice: the first in the backlog
that is not `Done`. There is no argument and no separate "next" command. If a
slice is already `In progress`, the run resumes it from its `Notes`.

1. Branch from the latest `main` and set the slice to `In progress`.
2. Write failing tests from the acceptance criteria: e2e for the slice's main
   path, unit tests for core logic.
3. Write code until `make check` and `make e2e` pass.
4. Run the `slice-reviewer` agent once and fix its findings.
5. Update the affected documents, set the slice to `Done`, and open a pull
   request with the review result in the description. Enable auto-merge.
6. Wait for the merge, then stop and tell the human to run `/clear` and
   `/nightshift:build` again. When no slice is left, tell the human to run
   `/nightshift:release` instead.

A failed fix is recorded in the slice's `Notes`. After three failed fixes of
the same problem, the skill stops and asks the human.

The skill itself launches no agent other than the reviewer in step 4. It
neither asks for nor forbids the subagents that Claude Code starts on its own
to search or read code; those keep the main context small.

The skill stops after each slice because agent quality drops as context
grows, and only the human can clear the context of a visible session. Every
slice therefore starts clean, reading its state from the backlog, and the
human keeps a live view of the work. The unit of the skill is one slice, so a
driver that repeats it without the human can be added later without changing
the skill.

### The slice reviewer

`agents/slice-reviewer.md` defines a read-only agent. Its prompt gives it the
branch diff, the slice's backlog section, and `docs/architecture.md`, and
nothing else. It returns a list of findings, each marked as blocking or not,
against four questions: are the acceptance criteria met, are modules deep with
no leaking interfaces, are the tests meaningful, and are there obvious
security problems.

## Scripts

`scripts/nightshift.py` has three subcommands, so that skills never spend
tokens on what can be computed:

| Subcommand | Result |
|---|---|
| `gate <doc>...` | Exit 0 if every document is `Approved`; otherwise names the ones that are not |
| `next` | Prints the section of the next slice to build, or reports that none is left |
| `set-status <slice> <status>` | Updates one slice's status in the backlog |

The same file is the one place that knows the target project contract: the
marker file, the gated paths, and how a status line is read and approved.
Hooks import it instead of repeating those rules.

`templates/check-docs.py` is the document sync check. `build` copies it into
the project as `scripts/check-docs.py` so that CI can run it without the
plugin installed (see [ADR 0003](adr/0003-vendor-the-document-check.md)). It
fails when:

- a gated document has no valid `Status` line;
- a backlog section is malformed, or more than one slice is `In progress`;
- a `Done` slice has no pull request number;
- a relative link in `docs/` points to a file that does not exist.

## Hooks

All hooks exit immediately when the project has no `.nightshift` marker, so
the plugin can stay enabled in unrelated repositories.

| Hook | Event | Blocks when |
|---|---|---|
| Gate protection | `PreToolUse` on `Edit`, `Write`, `Bash` | An edit would leave a file with an approved status line that it does not have now, or a shell command contains the text `Status: Approved` |
| `main` protection | `PreToolUse` on `Bash` | `git commit` while on `main`, `git push` to `main`, or any force push |
| Check before stopping | `Stop` | A slice is `In progress` and `make check` fails |

A fourth hook does not block anything; it is how the human approves:

| Hook | Event | Does |
|---|---|---|
| Approval | `UserPromptSubmit` | When the whole prompt is `approve` or `approved`, sets every gated document that is `Draft` to `Approved` and reports the list to the agent |

This event fires only for text the human submits, and the hook edits the files
itself rather than through an agent tool call. The agent therefore cannot
trigger it, and gate protection does not get in its way. Because stages run in
order, the `Draft` documents at any moment are exactly the ones waiting at the
current gate. Any other prompt, such as feedback on the draft, passes through
untouched.

Details:

- Gate protection decides on the result of an edit, not on its text: it
  applies the edit in memory and blocks when the file would gain an approved
  status line. Replacing the single word `Draft` is therefore blocked, and
  quoting the status in a document body is not.
- Gate protection also blocks shell commands that start a nested `claude`
  session, since a prompt submitted there would count as human input.
- The stop hook keeps a count of consecutive failures in `.git/nightshift/`,
  which is never committed. On the third failure it lets the agent stop and
  tells it to ask the human. A passing run resets the count.
- The stop hook skips `make check` when the working tree is unchanged since
  the last passing run.
- Matching shell commands is best effort. It stops mistakes, not a determined
  bypass. Server-side branch protection, set up in the walking skeleton, is the
  real guarantee for `main`.

## Templates

`templates/` holds the files that skills copy into a project: the requirements
document, architecture document, ADR, backlog, delivery report, pull request
description, a short project `CLAUDE.md`, and `check-docs.py`. There is no CI
or Makefile template, because those depend on the toolchain; the walking
skeleton slice writes them to satisfy the contract above.

## Implementation language

Hooks and scripts are Python 3 using only the standard library, so the plugin
needs no install step (see [ADR 0001](adr/0001-python-standard-library.md)).
Development uses `ruff` for format and lint and `pytest` with coverage, run
through `uv`, which installs them from `pyproject.toml` on first use.

## Testing this repository

| Level | Covers | How |
|---|---|---|
| Unit | Backlog and status parsing, each `check-docs` rule, each hook's decision | `pytest`, through each script's command-line interface |
| Structure | Manifests are valid, every skill has frontmatter and stays under a line budget, every template that a skill names exists | `pytest` |
| End to end (`make e2e`) | Hooks and scripts against a temporary git repository that plays a target project through all stages | `pytest`, with hook input fed as Claude Code sends it |
| Skills | Whether the prompts produce the intended behavior | Building `cellar`; problems found there become slices here |

No test calls a model, so CI is free and deterministic (see
[ADR 0004](adr/0004-no-model-calls-in-ci.md)). The coverage floor for
`hooks/` and `scripts/` is 85%.

## How this repository uses its own workflow

`nightshift` follows the same stages and file formats as a target project,
with one difference: until a stage's skill exists, that stage is done by hand
following this document.

## Planned slices

The slices and their acceptance criteria are in [backlog.md](backlog.md). In
short:

1. Walking skeleton: a loadable plugin and marketplace, the `spec` skill with
   its template, the `gate` subcommand, gate protection, the approval hook,
   `make check`, and CI with required checks.
2. `main` protection.
3. `design` and `slice`, with their templates and the `next` and `set-status`
   subcommands.
4. `check-docs.py`.
5. `build`, without review.
6. Check before stopping.
7. The slice reviewer.
8. `release`.

`cellar` is created after slice 1 and follows one stage behind, so each skill
is tried on a real project as soon as it exists.
