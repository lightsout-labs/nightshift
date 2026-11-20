# Changelog

## v0.1.0 - 2026-11-20

- `/nightshift:spec` asks clarifying questions and writes the requirements, which only the human can approve by typing `approve` (#3)
- Commits on `main`, pushes to it, and force pushes are blocked (#4)
- `/nightshift:design` and `/nightshift:slice` write the architecture, ADRs, and a backlog of vertical slices behind the design gate (#5)
- `make check` reports documents that are out of sync with each other (#6)
- `/nightshift:build` builds one slice test first and opens a pull request that merges itself (#7)
- The agent cannot stop in the middle of a slice while `make check` fails (#8)
- Each slice is reviewed once by a separate read-only agent before its pull request (#9)
- `/nightshift:release` tags, deploys, and writes a delivery report for the human to accept (#11)
- `spec` writes `LICENSE`, `README.md`, and settings that enable the plugin for the project (#12)
- `build` reports context and plan usage after each slice, and notes can address later slices (#14)
- `spec` handles requirement changes in a project under way, behind one gate (#15)
- Design is split into a short architecture document and per-module design files (#16)
- `/nightshift:fix` turns GitHub issues that report defects into fix slices without a gate (#18)
- `.nightshift` settings choose the document language, whether there is CI, and whether `build` stops after each slice (#19)
