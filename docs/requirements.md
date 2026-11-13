# Requirements

Status: Approved

## Original requirements

Translated from the owner's original notes.

1. Create an automated workflow for solo software development using AI agents
   such as Claude Code, similar to the current "software factory" concept.
2. The human only reviews the requirements document and the architecture and
   design documents, and accepts the final delivery. The AI is responsible for
   writing all documents, the build, unit tests, end-to-end (e2e) tests, CI,
   releases, and everything else.
3. Save tokens. Do not launch a crowd of agents. Run through to the end, pausing
   only where human confirmation is part of the workflow.
4. Requirements gathering must ask the human follow-up questions, so that the
   human and the agent reach agreement on the requirements.
5. All documents and code comments are written in English. Documents must be
   kept in sync at the end of every task.
6. Development is iterative: tasks are decomposed sensibly and delivered in
   small steps.
7. Use TDD: write test cases from the requirements first, then write the code
   that makes them pass.
8. Decompose work vertically, not horizontally. Every task must be testable
   end to end.
9. Prefer deep modules over shallow modules, and make full use of established
   design best practices.
10. The code structure must be sound, and formatting and lint checks must pass.
11. Unit test coverage must be sufficient to exercise all core logic, without
    chasing a meaningless 100% line coverage. No redundant or meaningless test
    cases.
12. E2e tests cover most end-to-end business flows, balancing coverage against
    cost.
13. The first example is an Excel-like spreadsheet editor. The web version has
    the highest priority, and it must be easy to add macOS, Linux, and Windows
    versions later.
14. More examples can be added later to validate the workflow.
15. Once validated, the plan is to build an online tutorial that demonstrates
    the workflow.
16. Decide how many repositories are needed and how to name them; the owner
    then creates them on GitHub.
17. Do not over-engineer. Always choose the simplest design that meets the
    requirements, in the architecture and the design as well as in the code.

## Decisions so far

These were agreed during planning and refine the requirements above.

- **Form**: the factory is a Claude Code plugin named `nightshift`. Its
  repository doubles as the plugin marketplace, so no central registry is
  needed.
- **Repositories** (GitHub organization `lightsout-labs`):
  - `nightshift`: the plugin (skills, document templates, check scripts).
  - `cellar`: the first example, a spreadsheet editor.
  - A tutorial site repository, created after the workflow is validated.
- **Separation**: the factory lives in its own repository from the start, so
  each example repository's history is clean evidence of the workflow.
- **Workflow**: five stages (`spec`, `design`, `slice`, `build`, `release`)
  with three human gates: requirements approval, design approval, and final
  acceptance.
- **Integration**: one pull request per vertical slice, squash-merged, with
  auto-merge once CI is green.
- **First example stack**: TypeScript for `cellar`. Rust is reserved for a
  later example, to show that the factory is language-agnostic.
- **Language-agnostic contract**: the factory relies on a single `make check`
  entry point in each project and does not depend on a specific toolchain.
- **Progress state**: each project keeps its backlog and slice status in
  Markdown files under `docs/`, versioned with the code. The files are the only
  source of truth; a slice starts from a fresh context by reading them.
- **`make check` scope**: format check, lint, unit tests, a coverage threshold,
  and a document sync check. It must be fast enough to run on every change.
  - The coverage threshold is set per project in its design document and
    applies to core logic. It is a floor against regressions, not a target.
  - The document sync check fails on stale documents, such as a gated document
    without a `Status` header or a finished slice whose backlog entry is not
    updated.
- **E2e tests**: a separate `make e2e` target, kept out of `make check` so the
  local loop stays fast. It runs before a slice's pull request is opened and as
  a required CI check.
- **Retry limit**: during `build`, the agent stops and asks the human after
  three failed attempts to fix the same problem.
- **Fresh context per slice**: `build` builds one slice per run and then
  stops. The human clears the context and runs it again. Agent quality drops
  as context grows, and a visible session cannot clear itself; a headless
  driver was rejected for now because the human would lose the live view.
  This is a deliberate pause in addition to the three gates.
- **Single-agent rule**: the workflow never splits its work across several
  agents or runs agents in parallel. This does not restrict the subagents that
  Claude Code starts on its own, for example to search or read code. They keep
  the main context small, which serves the same goal of saving tokens.
- **Independent code review**: because the human does not review code, each
  slice gets one review by a separate agent. This is the only agent the
  workflow itself launches.
  - It runs once per slice, after `make check` and `make e2e` pass and before
    the pull request is opened.
  - The reviewer starts from a fresh context and reads only the diff, the
    slice's backlog entry, and the architecture document.
  - It checks what scripts cannot: conformance to the acceptance criteria,
    module depth, interface leaks and over-engineering, meaningful tests, and
    obvious security problems.
  - There is a single round. Findings are fixed without a second review, and
    failed fixes count toward the retry limit.
  - The review result is recorded in the pull request description.
- **Simplest design**: it applies at every level. `spec` adds no requirement
  the human did not ask for, `design` chooses the fewest components, layers,
  and dependencies that meet the requirements, `slice` plans nothing beyond
  them, `build` writes nothing that the slice's criteria do not need, and
  the review reports what goes beyond them. A need that the requirements
  state, such as a later platform, is not speculation. The rule limits scope
  and structure, not quality: `spec` still raises what seems missing as a
  question, a deep module with one caller is not over-engineering, and
  errors and edge cases are handled with care.
- **Ambition is agreed in `spec`**: the agent's ideas, such as a feature the
  human did not think of or a more polished UI, are proposed during `spec`
  as options. What the human accepts becomes a numbered requirement with an
  observable quality bar, `slice` turns it into acceptance criteria in every
  slice it applies to, and `build` must meet them. Later stages invent
  nothing.
- **Design practices**: besides deep modules, `design` keeps core logic free
  of I/O, UI, and framework code, and gives each piece of knowledge one
  owning module. Other practices are used only where a requirement calls for
  them.
- **Rules outside the skills**: the project's `CLAUDE.md` repeats the rules
  on simplicity, deep modules, and tests in one line each, so they also hold
  for work done without a skill.
- **Repository documents**: there is no separate initialization command;
  `spec` is where a project starts. It asks for the license and writes
  `LICENSE` and a first `README.md` with the requirements. The walking
  skeleton adds how to run the project to the `README.md` and writes
  `CLAUDE.md`, because the commands are not known before the design.
- **Plugin loading**: `spec` writes a `.claude/settings.json` that enables
  the plugin for the project. A session that is resumed or started without
  the plugin would otherwise run without the hooks, and nothing could report
  it: `approve` would silently do nothing.
- **Backlog size**: `release` moves the finished slices to
  `docs/backlog/vX.Y.Z.md`, so `docs/backlog.md` holds only the release in
  progress.
- **Hooks**: the plugin ships four hooks, so these rules are enforced
  deterministically rather than by prompt.
  - Gate protection: the agent cannot set a document to `Status: Approved`.
    Only the human approves.
  - Approval: the human approves by typing `approve` in Claude Code. A hook on
    the human's prompt changes the status, so the agent cannot trigger it.
  - `main` protection: commits on `main`, direct pushes to it, and force pushes
    are blocked locally.
  - Check before stopping: during `build`, the agent cannot stop while
    `make check` fails, bounded by the retry limit.
  - There is no format-on-edit hook; `make check` already covers formatting.
- **Deployment of `cellar`**: the web version is deployed to GitHub Pages by
  the `release` stage.
