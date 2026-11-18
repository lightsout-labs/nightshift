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
  build/walking-skeleton.md
                       What only the first slice needs, read only then
  spec/change.md       How spec changes a project under way, read only then
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
A skill continues into another by reading that skill's file and following it:
`spec` into `design` after the requirements gate, and `design` into `slice`.

## Target project contract

Everything the plugin knows about a project is in this section. Skills, hooks,
and scripts depend on nothing else.

### Files

| Path | Written by | Gated |
|---|---|---|
| `.nightshift` | `spec` | No. Empty marker file; hooks do nothing without it |
| `.claude/settings.json` | `spec` | No. Enables the plugin, so every session in the project loads the hooks, and sets the status line that records usage |
| `LICENSE` | `spec` | No. The license the human chose; absent if they want none |
| `README.md` | `spec`, completed by `build` in the walking skeleton | No. Goal first; how to run, test, and deploy once that exists |
| `docs/requirements.md` | `spec` | Yes |
| `docs/architecture.md` | `design` | Yes |
| `docs/adr/NNNN-<title>.md` | `design`, `build` | No |
| `docs/design/<module>.md` | `design`, `build` | No. The decisions inside one module of the architecture document, each with its reason; created when a module has its first one |
| `docs/backlog.md` | `slice`, updated by `build` | Yes |
| `docs/backlog/vX.Y.Z.md` | `release` | No. The finished slices of one release |
| `docs/delivery/vX.Y.Z.md` | `release` | Yes; approval is the acceptance |
| `CHANGELOG.md` | `release` | No. One section per version, newest first |
| `scripts/check-docs.py` | `build`, in the walking skeleton | No |
| `CLAUDE.md` | `build`, in the walking skeleton | No. Commands and rules for a fresh context |

A gated document has `Status: Draft` or `Status: Approved` as the first line
after its title. The human approves by typing `approve` in Claude Code (see
[Gates](#gates)). The architecture document and the backlog are approved
together at the design gate.

Design is in two levels, so that a slice reads only what it needs (see
[ADR 0005](adr/0005-design-in-two-levels.md)). The architecture document
holds what spans modules, and every slice reads it. A module's file in
`docs/design/` holds the decisions inside that module, and only the slices
that touch the module read it. It has no status: like an ADR, it records
decisions made while building, within the approved architecture.

### Backlog format

`docs/backlog.md` is the only record of progress. Each slice is one section:

```markdown
## S03: Edit a cell and see dependent cells update

Status: Todo | In progress | Done

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
  slice, failed fix attempts, and CI failures with their fixes. It is added
  when there is something to record.
- A note meant for a later slice names it by number, such as `S13`.
  `nightshift.py next` prints it with that slice, which therefore sees it
  without reading the rest of the backlog.
- The pull request of a slice is found from its squashed commit on `main`,
  whose title ends with `(Snn) (#n)`. Backlogs written before may also have
  a `PR: #n` line, which nothing reads.
- `release` moves the slices of a release to `docs/backlog/vX.Y.Z.md`, so
  the backlog holds only the release in progress and stays readable. Slice
  numbers continue across releases.

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
| `spec` | Nothing | Asks clarifying questions until no requirement is ambiguous, proposes features and quality bars for the human to accept or decline, then writes `docs/requirements.md` from the template, `LICENSE`, a first `README.md`, and `.claude/settings.json`. In a project under way (requirements approved, backlog exists), changes the requirements, the architecture where needed, and the backlog on one branch | Stops at the requirements gate |
| `design` | Requirements approved | Writes `docs/architecture.md` and ADRs, then runs `slice` | Stops at the design gate |
| `slice` | Requirements approved, architecture exists | Writes `docs/backlog.md`: a walking skeleton first, then vertical slices with acceptance criteria | Returns to `design`, or stops at a gate for the backlog if run alone |
| `build` | Architecture and backlog approved | Builds the next slice (see below) | Stops after one slice |
| `release` | All slices `Done` | Tags a version, writes the changelog, deploys, archives the backlog, writes the delivery report | Stops at the acceptance gate |

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
| Requirements | Starts `design` in the same session; the clarifying answers are useful context for it. For a change to a project under way, stops and asks for `/clear` and `/nightshift:build` |
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
3. Write code until `make check` and `make e2e` pass, with nothing beyond
   the slice's criteria.
4. Update the affected documents, so that the review covers them, then run
   the `slice-reviewer` agent once and fix its findings.
5. Record in `Notes` what later slices need, set the slice to `Done`, and
   push once; then open a pull request with the review result in the
   description and enable auto-merge. A second push would start CI again
   and cancel the first run. A failing check is fixed, and recorded in
   `Notes`, in the same pull request.
6. Wait for the merge, then stop and tell the human to run `/clear` and
   `/nightshift:build` again, with the line that `nightshift.py usage`
   prints. When no slice is left, tell the human to run
   `/nightshift:release` instead.

A failed fix is recorded in the slice's `Notes`. After three failed fixes of
the same problem, the skill stops and asks the human.

When the backlog has no slices at all, which is its state between releases,
`nightshift.py next` says so. `build` and `release` then have nothing to do
and name `/nightshift:spec`, which starts the next release.

`build` needs a GitHub remote and `gh`, because it opens and merges pull
requests. In every slice it compares the project's `check-docs.py` with
the plugin's by `--version` and copies a newer one.

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

`agents/slice-reviewer.md` defines a read-only agent: its only tool is
`Read`. It reads the branch diff, the slice's backlog section,
`docs/architecture.md`, and the design of the modules the slice touches, and
nothing else. It returns a result line and a
list of findings, each marked as blocking or minor, against four questions:
are the acceptance criteria met, are modules deep with no leaking interfaces
and nothing built beyond the criteria, are the tests meaningful, and are
there obvious security problems.

`build` hands over the first two as files, `.git/nightshift/review.diff` and
`.git/nightshift/slice.md`, which it writes with `git diff main...HEAD` and
`nightshift.py next`, and the last as `.git/nightshift/design.md`, the
modules' files in `docs/design/` one after another, because the reviewer
cannot list a directory and the builder knows which modules it touched.
The reviewer therefore needs no shell, and the builder
never repeats the diff as prompt text. The prompt is the fixed sentence
"Review the slice.", so nothing of the builder's view of its own work reaches
the reviewer.

There is one round. `build` runs `make check` on the updated documents
before the review, and saves the reviewer's reply as
`.git/nightshift/review-Snn.md`. It then fixes every blocking finding and
each minor one that is right. A resumed run that finds the file does not
review again and carries on with the findings in it. The findings and what
was done about each go into the pull request description.

### Releasing

`/nightshift:release` runs when every slice is `Done`, and has two pull
requests, because the version is tagged on `main` and the human accepts
something that is already deployed:

1. Choose the version: `v0.1.0` first, then the latest tag with the minor
   number raised, the patch number when every slice is a fix, or the major
   number only when the requirements say the release breaks compatibility.
2. On the branch `chore/release-vX.Y.Z`: add the version's section to
   `CHANGELOG.md`, with one line per slice, set the version where the project
   records it, and run `nightshift.py archive`. The pull request merges
   itself when CI is green.
3. Tag the merged `main` and push the tag, then deploy and verify as the
   project's architecture document describes. A failed deployment is fixed
   through a pull request of its own; a tag is never moved, so the fix is
   tagged and deployed as the next patch version, which the report names.
4. On the branch `docs/delivery-vX.Y.Z`: write the delivery report from the
   template as a draft, open a pull request, and stop at the acceptance gate.
5. On `approve`, commit the status, merge, and stop. The release is closed.

The report lists every requirement with its result and the slices that
deliver it, how to try the delivery, and known limits. At the gate, a change
to the report is applied; a change to the product belongs to the next release
and is recorded under known limits.

The files are the state, so an interrupted run resumes: a `Draft` report
on a `docs/delivery-vX.Y.Z` branch means the release waits at the gate, and
otherwise an archived backlog with no report of the same version means the
run stopped between steps 2 and 4. Like
`build`, `release` needs a GitHub remote and `gh`.

## Scripts

`scripts/nightshift.py` has five subcommands, so that skills never spend
tokens on what can be computed:

| Subcommand | Result |
|---|---|
| `gate <doc>...` | Exit 0 if every document is `Approved`; otherwise names the ones that are not |
| `next` | Prints the section of the next slice to build, followed by the `Notes` items of earlier slices that name it; or reports that none is left, or that the backlog has no slices |
| `set-status <slice> <status>` | Updates one slice's status in the backlog; refuses a second slice `In progress` |
| `archive <version>` | Moves every slice to `docs/backlog/<version>.md`, leaving the backlog's title, status, and introduction; refuses when a slice is not `Done`, when there is none, or when the file exists |
| `usage` | Prints the context, 5-hour, and weekly usage, such as `Context 43% · 5h 27% · week 61%`, as the status line last recorded it |

`next`, `set-status`, and `archive` read `docs/backlog.md` under the current
directory, so skills run them from the project root. All fail, naming the
slice, when a slice has no valid status line. `archive` moves the text as it
is, so a relative link inside a slice breaks and the document check reports
it.

Claude Code passes the context and plan usage only to a status line command,
not to hooks or tools. The project's status line, from the settings template,
therefore saves its input to `.git/nightshift/usage.json` and displays
nothing, and `usage` reads that file. A value Claude Code did not pass, such
as plan limits in a session that uses an API key, prints as `?`; without the
file, `usage` says how to add the status line. It always exits 0, because the
report is information, not a check.

The same file is the one place that knows the target project contract: the
marker file, the gated paths, how a status line is read and approved, and
how the backlog is split into slices.
Hooks import it instead of repeating those rules.

`templates/check-docs.py` is the document sync check. `build` copies it into
the project as `scripts/check-docs.py` so that CI can run it without the
plugin installed (see [ADR 0003](adr/0003-vendor-the-document-check.md)). It
fails when:

- a gated document has no valid `Status` line;
- a backlog section is malformed, or more than one slice is `In progress`;
- a relative link in `docs/` points to a file that does not exist.

It takes no arguments, reads `docs/` under the current directory, and prints
one line per problem, so one run shows everything there is to fix. Documents
that do not exist yet are not a problem, which lets it run from the first
slice on. A backlog section is malformed when its heading is not
`## Snn: title`, its number is used twice, its status line is missing or
unknown, or it has no acceptance criteria. Links are checked for the file
only, not for the anchor, and links quoted as code are not read.

Because the copy must run alone, it repeats the status and backlog rules of
`nightshift.py` instead of importing them. The end-to-end test runs both on
the same project, so they cannot drift apart unnoticed. `VERSION` in the file
is a whole number, raised with every change to its behavior, and
`check-docs.py --version` prints it.

## Hooks

All hooks exit immediately when the project has no `.nightshift` marker, so
the plugin can stay enabled in unrelated repositories.

| Hook | Event | Blocks when |
|---|---|---|
| Gate protection | `PreToolUse` on `Edit`, `Write`, `Bash` | An edit would leave a file with an approved status line that it does not have now, or a shell command contains the text `Status: Approved` |
| `main` protection | `PreToolUse` on `Bash` | `git commit` while on `main`, `git push` to `main`, or any force push |
| Check before stopping | `Stop` | A slice is `In progress` and `make check` fails, up to twice in a row |

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
  quoting the status in a document body is not. A shell command is matched
  on its text, so it also blocks setting a document back to `Draft` that
  way; its message points the agent to the Edit tool instead.
- Gate protection also blocks shell commands that start a nested `claude`
  session, since a prompt submitted there would count as human input.
- `main` protection judges each git command by the branch it would run on,
  following `cd`, `git -C`, and `git switch` or `git checkout` earlier in the
  same command line. `git switch -c feat/x && git commit` is therefore allowed
  on `main`. A commit on a detached `HEAD` is allowed.
- A push is to `main` when a refspec's destination is `main`, when it has no
  refspec and the current branch is `main`, or when it pushes every branch
  (`--all`, `--mirror`). Pushing tags is allowed from any branch. A force push
  is any `--force...` option, `-f`, or a `+` refspec.
- The stop hook runs `make check` from the project root and blocks with the
  end of its output, where a failing check names what failed. It keeps a
  count of consecutive failures in `.git/nightshift/`, which is never
  committed. A passing run resets the count.
- The third failure in a row does not block. Claude Code delivers a hook's
  text to the agent only by continuing the turn, so the hook returns the
  output as feedback that tells the agent to ask the human, and lets the
  next stop through without running the check. The count then starts again,
  so the agent has three attempts after the human answers.
- The stop hook skips `make check` when the working tree is unchanged since
  the last passing run. It compares a hash of every file that git does not
  ignore, committed or not, which it takes by staging the files in an index
  of its own under `.git/nightshift/`. The project's index is not touched.
- The stop hook does nothing outside a git repository, and nothing when the
  backlog is missing or cannot be read: without a slice `In progress` there
  is no build to guard.
- Matching shell commands is best effort. It stops mistakes, not a determined
  bypass. Server-side branch protection, set up in the walking skeleton, is the
  real guarantee for `main`.

## Templates

`templates/` holds the files that skills copy into a project: the requirements
document, architecture document, ADR, backlog, delivery report, pull request
description, a short project `CLAUDE.md`, `check-docs.py`, and the project's
`settings.json`. There is no CI or Makefile template, because those depend on
the toolchain; the walking skeleton slice writes them to satisfy the contract
above. `README.md` and `LICENSE` have no template either: the first depends
on the project, and the agent knows the text of the common licenses.

`settings.json` names this repository as a marketplace and enables the
plugin from it. Claude Code then offers to install the plugin when the
project is trusted, and loads it in every session there, including one that
is resumed. Without it, a session started without the plugin has no hooks,
and typing `approve` does nothing. Its status line records usage for
`nightshift.py usage`; as a project setting, it replaces the human's own
status line in that project only.

## Implementation language

Hooks and scripts are Python 3 using only the standard library, so the plugin
needs no install step (see [ADR 0001](adr/0001-python-standard-library.md)).
Development uses `ruff` for format and lint and `pytest` with coverage, run
through `uv`, which installs them from `pyproject.toml` on first use.

## Testing this repository

| Level | Covers | How |
|---|---|---|
| Unit | Backlog and status parsing, each `check-docs` rule, each hook's decision | `pytest`, through each script's command-line interface |
| Structure | Manifests are valid, every skill has frontmatter and stays under a line budget, every plugin file that a skill names exists, the settings template names this marketplace and plugin, the reviewer is the only agent, has no tool but `Read`, and is named only by `build` | `pytest` |
| End to end (`make e2e`) | Hooks and scripts against a temporary git repository that plays a target project through all stages | `pytest`, with hook input fed as Claude Code sends it |
| Skills | Whether the prompts produce the intended behavior | Building `gridworks`; problems found there become slices here |

No test calls a model, so CI is free and deterministic (see
[ADR 0004](adr/0004-no-model-calls-in-ci.md)). The coverage floor for
`hooks/`, `scripts/`, and `templates/check-docs.py` is 85%.

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

`gridworks` is created after slice 1 and follows one stage behind, so each skill
is tried on a real project as soon as it exists.
