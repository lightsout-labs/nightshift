# nightshift

A Claude Code plugin that runs a solo "software factory". You review the
requirements and the design, and you accept the delivery. The agent does
everything else: documents, code, tests, CI, and releases.

> **Status**: under construction. The `spec` and `design` stages, their
> gates, `main` protection, and the document check work today. The other stages are built slice
> by slice; see [docs/backlog.md](docs/backlog.md).

## Install

In Claude Code:

```
/plugin marketplace add lightsout-labs/nightshift
/plugin install nightshift@lightsout-labs
```

The plugin needs `python3` on the path and nothing else. For pull requests it
uses the GitHub CLI, `gh`, if the project has a GitHub remote.

## Workflow

Each stage is one command. You are asked for a decision at three gates and
nowhere else.

| Stage | Command | The agent produces | Your part |
|---|---|---|---|
| Spec | `/nightshift:spec` | `docs/requirements.md`, after asking you clarifying questions | Approve |
| Design | `/nightshift:design` | `docs/architecture.md`, ADRs, and a backlog of vertical slices | Approve |
| Build | `/nightshift:build` | One slice per run: tests first, then code, then a pull request that merges itself when CI is green | Run `/clear` and the command again |
| Release | `/nightshift:release` | A tagged version, a changelog, a deployment, and a delivery report | Accept |

`/nightshift:spec` and `/nightshift:design` exist so far. After you approve
the requirements, design starts in the same session, so you normally type
only the first command. `/nightshift:slice` rewrites the backlog alone, for
when the plan changes after the design is approved.

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

A project opts in through an empty `.nightshift` file in its root, which
`/nightshift:spec` creates. Without it the hooks do nothing, so the plugin can
stay enabled everywhere.

## How it is built

- [docs/requirements.md](docs/requirements.md): what the plugin must do.
- [docs/architecture.md](docs/architecture.md): skills, scripts, hooks, and
  the contract with a target project.
- [docs/backlog.md](docs/backlog.md): the slices and their status.

## Development

Requires [uv](https://docs.astral.sh/uv/) and `make`.

```sh
make check    # format, lint, document check, unit and structure tests, coverage
make e2e      # hooks and scripts against a temporary git repository
make format   # apply formatting and lint fixes
claude --plugin-dir .    # try the working copy in a session
```

No test calls a model. What the skills do is checked by building the example
project, `lightsout-labs/cellar`. Branching and commit rules are in
[docs/branching.md](docs/branching.md).

## License

[MIT](LICENSE)
