# 0005: Design in two levels

## Context

`build` reads `docs/architecture.md` at the start of every slice, and the
slice reviewer reads it too. Each slice also records its decisions there, so
the document grows with the project. In `gridworks` it reached 65 KB after
30 slices, 700 of its 870 lines in the Modules section: how undo records a
change, how a paste works out its cells, how the grid draws a merged cell.
Every slice paid for all of it, though most touch one or two modules, and
the reviewer's attention was spread over decisions the diff never reached.

## Decision

The architecture document holds what spans modules: the parts, the stack,
the module table with each interface, the boundaries, data, layout, testing,
and deployment, and the decisions that involve more than one module. The
decisions inside one module, each with its reason, go in
`docs/design/<module>.md`. A slice reads the architecture document and the
files of the modules it touches; `build` hands the same files to the
reviewer as `.git/nightshift/design.md`.

Module files are not gated. Like ADRs, they record decisions made while
building within the approved architecture; a change to the architecture
itself still goes through the architecture document.

## Consequences

- What a slice reads grows with the modules it touches, not with the
  project.
- The builder chooses which module files to read and hand over. Choosing
  too few hides a decision from the slice; the module table, which every
  slice reads, names the modules to choose from.
- A project designed before this change keeps working; moving its decisions
  out of the architecture document is a change of its own.

Rejected:

- One detailed design document beside the architecture: it grows the same
  way and every slice would read it.
- Decisions as comments in the code: they explain a line, not a choice
  between designs, and the reviewer, who reads the diff, would not see those
  outside it.
