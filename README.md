# nightshift

A Claude Code plugin that runs a solo "software factory". You review the
requirements and the design, and you accept the delivery. The agent does
everything else: documents, code, tests, CI, and releases.

> **Status**: v0.1.0, the first release; see [CHANGELOG.md](CHANGELOG.md).
> What the skills do is being verified by building `lightsout-labs/gridworks`;
> see [docs/backlog/v0.1.0.md](docs/backlog/v0.1.0.md).

## Install

In Claude Code:

```
/plugin marketplace add lightsout-labs/nightshift
/plugin install nightshift@lightsout-labs
```

The plugin needs `python3` on the path and nothing else. For pull requests it
uses the GitHub CLI, `gh`, if the project has a GitHub remote. `build`
requires both.

## Workflow

Each stage is one command. You are asked for a decision at three gates and
nowhere else.

| Stage | Command | The agent produces | Your part |
|---|---|---|---|
| Spec | `/nightshift:spec` | `docs/requirements.md`, after asking you clarifying questions | Approve |
| Design | `/nightshift:design` | `docs/architecture.md`, ADRs, and a backlog of vertical slices | Approve |
| Build | `/nightshift:build` | One slice per run: tests first, then code, one review by a separate read-only agent, then a pull request that merges itself when CI is green | Run `/clear` and the command again, unless the project builds every slice in one run |
| Release | `/nightshift:release` | A tagged version, a changelog, a deployment, and a delivery report | Accept |

After you approve the requirements, design starts in the same session.
`/nightshift:build` builds one slice and stops, so that each slice starts
from a clean context; it resumes a slice that was interrupted. A project can
choose instead to have it build every slice in one run (see
[Settings](#settings)).
As it builds, it records the decisions inside each module in
`docs/design/<module>.md`, so the architecture document stays short.
`/nightshift:slice` rewrites the backlog alone, for when the plan changes
after the design is approved. To add or change a requirement later, run
`/nightshift:spec` again: it asks about the change, updates the requirements,
the design where needed, and the backlog in one pull request, and stops for
your `approve`. To fix bugs reported as GitHub issues, run
`/nightshift:fix` with their numbers, or alone for every open issue: each
issue that shows the product breaking an approved requirement becomes a fix
slice at the front of the backlog, with no gate, and its pull request closes
the issue; the others are named for `/nightshift:spec`.

`/nightshift:release` runs when every slice is done. It tags and deploys the
version, moves the finished slices to `docs/backlog/vX.Y.Z.md`, and writes
`docs/delivery/vX.Y.Z.md`: what was delivered against each requirement, how
to try it, and known limits. Typing `approve` there accepts the delivery.

### Gates

A document that needs your decision starts with `Status: Draft`. At a gate
the agent opens a pull request, tells you which documents to read, and stops.
You then either:

- reply with changes, which the agent applies before stopping again, or
- type `approve`, which sets the documents to `Status: Approved` and lets the
  agent carry on.

The agent cannot approve its own work. Approval happens in a hook that runs
only on what you type, and a second hook blocks the agent from writing an
approved status or starting a nested `claude` session to type it for you.

A third hook keeps the agent off `main`: it blocks a commit while on `main`,
a push to `main`, and any force push, so every change arrives as a pull
request. Keep branch protection enabled on the server as well; the hook stops
mistakes, not a determined bypass.

A fourth hook runs `make check` whenever the agent tries to stop in the
middle of a slice, and sends it back to work when the check fails. After
three failures in a row it lets the agent stop to ask you instead.

A project opts in through a `.nightshift` file in its root, which
`/nightshift:spec` creates. Without it the hooks do nothing, so the plugin can
stay enabled everywhere.

### Settings

`.nightshift` also holds the project's settings, which `/nightshift:spec`
asks for when it starts the project. Edit the file to change them later.

```
language: English
ci: yes
stop-after-slice: yes
```

- `language`: the language of the documents, such as `简体中文`. Code,
  comments, commit messages, and the few words that scripts read, such as
  `Status: Draft`, stay in English.
- `ci`: with `no`, the project has no CI, and a slice's pull request merges
  as soon as `make check` and `make e2e` pass locally. Switching after the
  first slice also means changing the CI workflow and branch protection.
- `stop-after-slice`: with `no`, `/nightshift:build` goes on through every
  slice in one run instead of stopping after each, and stops only at the end
  of the backlog, on an ambiguous criterion, or after three failed fixes.
  `/nightshift:spec` then also asks at what context size Claude Code should
  compact the session, and sets `CLAUDE_CODE_AUTO_COMPACT_WINDOW` in
  `.claude/settings.json`; change it there later. If the context still
  passes 80%, `build` stops between slices so you can `/clear`. Each slice
  reads its state from the files, not from the context.

A setting left out has the default shown above, so an empty file is valid.

There is no separate command to set a project up. `/nightshift:spec` also
asks for the license and writes `LICENSE`, a first `README.md`, and a
`.claude/settings.json` that enables the plugin for the project, so that a
resumed session still has the hooks. Its status line records the context and
plan usage, which `/nightshift:build` reports at the end of each slice, and
displays nothing; in that project it replaces your own status line. If `approve` ever does nothing, the
plugin is not loaded: check `/plugin`. The first slice completes the
`README.md` and writes the project's `CLAUDE.md`.

## How it is built

- [docs/requirements.md](docs/requirements.md): what the plugin must do.
- [docs/architecture.md](docs/architecture.md): skills, scripts, hooks, and
  the contract with a target project.
- [docs/backlog.md](docs/backlog.md): the slices of the release in progress;
  earlier releases are in `docs/backlog/`.
- [CHANGELOG.md](CHANGELOG.md): what each version changed.

## Development

Requires [uv](https://docs.astral.sh/uv/) and `make`.

```sh
make check    # format, lint, document check, unit and structure tests, coverage
make e2e      # hooks and scripts against a temporary git repository
make format   # apply formatting and lint fixes
claude --plugin-dir .    # try the working copy in a session
```

No test calls a model. What the skills do is checked by building the example
project, `lightsout-labs/gridworks`. Branching and commit rules are in
[docs/branching.md](docs/branching.md).

## License

[MIT](LICENSE)
