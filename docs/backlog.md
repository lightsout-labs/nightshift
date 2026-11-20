# Backlog

Status: Approved

Slices for the `nightshift` plugin, built in this order. The format is defined
in [architecture.md](architecture.md#backlog-format).

Two kinds of acceptance criteria appear below. Those about hooks, scripts, and
plugin structure are verified by `make check` and `make e2e`. Those about what
a skill does are marked *(by hand)* and are verified by running the skill on
`gridworks`, because no test calls a model.
