# Backlog

Status: Approved

Slices for the `nightshift` plugin, built in this order. The format is defined
in [architecture.md](architecture.md#backlog-format).

Two kinds of acceptance criteria appear below. Those about hooks, scripts, and
plugin structure are verified by `make check` and `make e2e`. Those about what
a skill does are marked *(by hand)* and are verified by running the skill on
`cellar`, because no test calls a model.

## S01: Walking skeleton: requirements gate, end to end

Status: Done
PR: #3

Acceptance criteria:
- `claude --plugin-dir .` loads the plugin and lists `/nightshift:spec`. The
  plugin and marketplace manifests pass the structure tests.
- `/nightshift:spec` asks clarifying questions, writes `docs/requirements.md`
  from the template with `Status: Draft`, creates `.nightshift`, opens a pull
  request, and stops *(by hand)*.
- `nightshift.py gate <doc>...` exits 0 only when every named document is
  `Approved`, and otherwise names the ones that are not.
- Gate protection blocks an `Edit`, `Write`, or `Bash` call that would add
  `Status: Approved`, and a `Bash` call that starts a nested `claude` session.
- The approval hook sets every `Draft` gated document to `Approved` when the
  prompt is exactly `approve` or `approved`, and reports the list. Any other
  prompt changes nothing.
- Both hooks do nothing in a repository without `.nightshift`.
- `make check` runs format, lint, unit and structure tests, and the 85%
  coverage floor. `make e2e` plays the requirements gate in a temporary git
  repository: draft, blocked agent approval, human approval, open gate.
- CI runs `check` and `e2e` on every pull request. Both are required on
  `main`, and auto-merge is enabled.
- `README.md` explains what the plugin is, how to install it, and the
  workflow.

Notes:
- `scripts/nightshift.py` holds the target project contract (marker, gated
  paths, status line); hooks import it rather than repeat it.
- Gate protection applies an edit in memory and blocks on the resulting
  status, so replacing only the word `Draft` is blocked too.
- Development tools run through `uv`; `plugin.json` has no version until the
  first release.
- `spec` already commits and merges after `approve`; starting `design` from
  there is left to S03.
- The *(by hand)* criterion is not yet verified; it is when `cellar` starts.

## S02: Protect `main`

Status: Done
PR: #4

Acceptance criteria:
- The hook blocks `git commit` while on `main`, `git push` to `main`, and any
  force push.
- It allows commits and pushes on other branches, and does nothing without
  `.nightshift`.
- `make e2e` covers each blocked and allowed case in a temporary repository.

Notes:
- `hooks/main_protection.py` is a second `PreToolUse` registration, for
  `Bash` only. The branch name is `nightshift.MAIN`.
- The hook follows `cd`, `git -C`, and `git switch`/`git checkout` within one
  command line, so branching and committing in one command works on `main`.
  A switch to a branch that does not exist locally is not followed.
- Commands are split with `shlex`, so quoted text such as a commit message is
  never read as a command. Unbalanced quotes fall back to a plain split.
- Only `commit` and `push` are checked; `merge`, `cherry-pick`, and `revert`
  on `main` are left to server-side protection.
- Pushing tags from `main` is allowed, because `release` tags there.

## S03: Design gate: architecture, ADRs, and backlog

Status: Done
PR: #5

Acceptance criteria:
- `/nightshift:design` refuses to run while the requirements are not
  `Approved` *(by hand)*.
- It writes `docs/architecture.md` and ADRs from the templates, then a
  backlog whose first slice is a walking skeleton and whose other slices are
  vertical, each with acceptance criteria. Then it stops at the design gate
  *(by hand)*.
- After `approve` at the requirements gate, `spec` merges its pull request
  and `design` starts in the same session *(by hand)*.
- After `approve` at the design gate, the skill merges and asks for `/clear`
  and `/nightshift:build` *(by hand)*.
- `nightshift.py next` prints the first slice that is not `Done`, or reports
  that none is left.
- `nightshift.py set-status` changes one slice's status and refuses to make a
  second slice `In progress`.
- `make e2e` extends the played project through the design gate.

Notes:
- `spec` and `design` chain by reading the next skill's file, because every
  skill has `disable-model-invocation` and cannot be started by the agent.
- Run alone, `slice` opens its own gate on the branch `docs/backlog` and sets
  an approved backlog back to `Draft`; `Done` slices are kept.
- `set-status` takes the status in any case, with a hyphen for the space, so
  `in-progress` needs no quoting.
- `next` exits 0 with a message when no slice is left; only a missing or
  malformed backlog is an error.
- The e2e test drafts the design from the templates, so a template that the
  scripts cannot parse fails the build.
- Without a remote, the skills fast-forward `main` after approval, since the
  `main` protection hook blocks a commit there.
- The four *(by hand)* criteria are not yet verified; they are when `cellar`
  reaches its design stage.

## S04: Document sync check

Status: Done
PR: #6

Acceptance criteria:
- `check-docs.py` fails, naming the file and the reason, when a gated
  document has no valid `Status` line, a backlog section is malformed, more
  than one slice is `In progress`, a `Done` slice has no pull request number,
  or a relative link in `docs/` is broken.
- It passes on a project whose documents are consistent.
- It is one file with no dependencies and carries a version line.
- This repository's own `make check` runs it on `docs/`.

Notes:
- The file is `templates/check-docs.py`. It takes no arguments, reads `docs/`
  under the current directory, and reports every problem in one run.
- "Malformed" is: a heading that is not `## Snn: title`, a slice number used
  twice, a missing or unknown status line, or no acceptance criteria.
- Links are checked for the file only, not the anchor. Links in code, web
  addresses, and paths that start with `/` are skipped.
- It repeats the status and backlog rules of `nightshift.py`, because the
  copy must run alone. The e2e test runs both on the same project.
- `VERSION` is a whole number and `--version` prints it, so `build` (S05) can
  compare a project's copy with the plugin's.
- A `Done` slice needs its pull request number, so `build` (S05) must open
  the pull request before it sets the slice to `Done`, not after.

## S05: Build one slice

Status: Done
PR: #7

Acceptance criteria:
- `/nightshift:build` refuses to run unless the architecture and the backlog
  are `Approved` *(by hand)*.
- It builds the first slice that is not `Done`: branch, failing tests first,
  code until `make check` and `make e2e` pass, documents updated, slice set
  to `Done`, pull request opened with auto-merge. Then it stops and asks for
  `/clear` and another run *(by hand)*.
- For a walking skeleton slice it also sets up the `Makefile`, CI with the
  `check` and `e2e` checks, branch protection, and deployment, and copies
  `check-docs.py` into the project *(by hand)*.
- Run on a slice that is `In progress`, it resumes from the slice's `Notes`
  *(by hand)*.
- It records failed fixes in `Notes` and stops to ask the human after three
  failures of the same problem *(by hand)*.
- When no slice is left, it asks for `/nightshift:release` *(by hand)*.
- The structure tests check the skill's line budget and that every template
  it names exists.

Notes:
- The skill is at the 80-line budget. S07 adds the review step, so it must
  shorten something else or raise the budget.
- New templates: `pull-request.md` (S07 adds the review result to it) and
  `CLAUDE.md`, which the walking skeleton fills in for the project.
- `build` requires a GitHub remote and `gh`; unlike `spec` and `design` it
  has no fallback, because a `Done` slice needs a pull request number.
- The pull request is opened first, then the slice is set to `Done` with its
  number in a second commit, so `make check` passes on the merged commit.
- A failing CI check counts as a failed fix toward the limit of three.
- The six *(by hand)* criteria are not yet verified; they are when `cellar`
  builds its first slices.

## S06: Check before stopping

Status: Done
PR: #8

Acceptance criteria:
- While a slice is `In progress`, the stop hook blocks stopping when
  `make check` fails and passes the failure output to the agent.
- On the third consecutive failure it allows the stop and tells the agent to
  ask the human. A passing run resets the count.
- It does not run `make check` when no slice is `In progress`, or when the
  working tree is unchanged since the last passing run.
- Its state is under `.git/nightshift/` and never appears in `git status`.

Notes:
- `hooks/check_before_stopping.py` is registered for `Stop` with the default
  timeout of 600 seconds; a `make check` that runs longer is not enforced.
- The third failure does not block. Claude Code gives a Stop hook's text to
  the agent only by continuing the turn, so the hook returns the output as
  `additionalContext` telling the agent to ask the human, and the stop after
  that passes without a run. The count then starts again from zero.
- "Unchanged" compares a tree hash of every file git does not ignore, taken
  through the hook's own index in `.git/nightshift/`, so uncommitted and
  untracked files count and the project's index is untouched.
- The hook does nothing outside a git repository or when the backlog cannot
  be read. Once `build` sets the slice to `Done`, the hook no longer runs.
- The `build` skill was not changed: the hook's messages say what to do.

## S07: Independent slice review

Status: Todo

Acceptance criteria:
- The `slice-reviewer` agent is read-only, and its definition passes the
  structure tests.
- `build` runs it once per slice, after `make check` and `make e2e` pass and
  before the pull request, giving it only the diff, the slice's backlog
  section, and the architecture document *(by hand)*.
- Blocking findings are fixed without a second review, and the review result
  appears in the pull request description *(by hand)*.

## S08: Release and acceptance

Status: Todo

Acceptance criteria:
- `/nightshift:release` refuses to run while any slice is not `Done`
  *(by hand)*.
- It tags `vMAJOR.MINOR.PATCH`, writes the changelog, deploys as the
  project's architecture document describes, writes
  `docs/delivery/vX.Y.Z.md` with `Status: Draft`, and stops at the acceptance
  gate *(by hand)*.
- The delivery report lists what was delivered against the requirements, how
  to try it, and known limits *(by hand)*.
- After `approve`, the skill merges the report and closes the release
  *(by hand)*.
- `make e2e` plays the full project through acceptance: the approval hook
  covers the delivery report, and gate protection covers `docs/delivery/`.
