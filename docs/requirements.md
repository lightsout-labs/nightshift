# Requirements

Status: Draft

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
