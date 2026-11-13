# nightshift

A Claude Code plugin that runs a solo "software factory": the human reviews
requirements and design and accepts the delivery; the agent does everything
else. Requirements and agreed decisions are in `docs/requirements.md`, and the
plugin's structure is in `docs/architecture.md`. Read both before making design
choices.

## What this repository is

- A Claude Code plugin, and its own plugin marketplace.
- The deliverables are skills, document templates, and check scripts. They are
  prompts and conventions for other projects, not an application.
- Projects built with it (the first is `lightsout-labs/cellar`) live in their
  own repositories.

## Workflow the plugin implements

| Stage | Output | Human gate |
|---|---|---|
| `spec` | Requirements document, after clarifying questions | Approve |
| `design` | Architecture document and ADRs | Approve |
| `slice` | Backlog of vertical slices with acceptance criteria | Reviewed with design |
| `build` | Code and tests, one PR per slice | None |
| `release` | Version, changelog, deployment, delivery report | Accept |

Gated documents carry a `Status: Draft | Approved` header. A stage must refuse
to run when the document it depends on is not approved.

## Principles to preserve when writing skills

- **Token economy**: one main agent. Skills never split work across agents or
  run agents in parallel; the only agent a skill launches is one fresh-context
  review agent per slice. Subagents that Claude Code starts on its own, for
  example to search code, are fine. Keep progress in files so a slice
  can start from a fresh context. Anything a script can decide (format, lint,
  coverage, doc sync) belongs in `make check`, and rules that must not be
  broken (gates, `main` protection) belong in hooks, not in a prompt.
- **Run to completion**: stop for the human only at the gates, on ambiguous
  requirements, after three failed fixes of the same problem, or between
  slices so the human can clear the context.
- **TDD**: failing tests first, then the code that passes them.
- **Vertical slices**: every slice is testable end to end. The first slice is a
  walking skeleton that includes CI, e2e, and deployment.
- **Deep modules**: small interfaces hiding substantial behavior. Tests go
  through public interfaces only.
- **Meaningful tests**: cover all core logic; no coverage chasing, no redundant
  cases. E2e covers main paths and key failures, not combinations.
- **Language-agnostic**: target projects expose `make check`; skills must not
  assume a toolchain.

## Conventions for this repository

- All documents, comments, and commit messages are in English.
- Update the affected documents in the same change as the behavior they
  describe.
- Never commit directly to `main`. One branch and one PR per change,
  squash-merged. Branch names and PR titles follow `docs/branching.md`.
- Keep skills short and specific. Every line in a skill costs tokens on every
  run.

## Local development

Load the plugin from a working copy without publishing it:

```sh
claude --plugin-dir /path/to/nightshift
```
