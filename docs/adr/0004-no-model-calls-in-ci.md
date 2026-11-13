# 0004: CI does not call a model

## Context

Most of the plugin is prompts. Testing their behavior automatically means
running an agent in CI, which costs tokens on every pull request, needs a
secret in a public repository, and gives results that vary between runs.

## Decision

Automated tests cover only hooks, scripts, and plugin structure. Skill
behavior is validated by building the example projects, starting with
`cellar`.

## Consequences

- CI is free, fast, and deterministic.
- A change to a skill can break behavior without failing CI. The example
  projects are the safety net, and problems found there become slices here.
- This can be revisited once the skills are stable enough to be worth
  regression tests.
