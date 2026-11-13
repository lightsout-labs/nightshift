# Architecture

Status: Draft

How <project> is built. What it must do is in
[requirements.md](requirements.md). Reasons for the decisions that are costly
to reverse are in the ADRs under `docs/adr/`.

## Overview

<One paragraph: the main parts and how one user action flows through them.>

## Stack

| Concern | Choice | Why |
|---|---|---|
| <Language, framework, storage, hosting> | <Choice> | <One line> |

## Modules

Each module has a small interface and hides substantial behavior. Tests go
through the interface only. Every module, layer, and dependency is here
because a requirement needs it.

| Module | Interface | Hides |
|---|---|---|
| <Name> | <The few operations callers use> | <What callers never see> |

## Data

<What is stored, where, and in what format.>

## Repository layout

```
<path>    <What it holds>
```

## Make targets

| Target | Contents |
|---|---|
| `make check` | <Format check, lint, unit tests, coverage floor of N%>, `scripts/check-docs.py` |
| `make e2e` | <How the end-to-end tests run> |

CI runs both on every pull request as the required checks `check` and `e2e`.

## Testing

| Level | Covers | How |
|---|---|---|
| Unit | <Core logic> | <Tool> |
| End to end | <Main paths and key failures> | <Tool> |

## Deployment

<Where it runs, what triggers a deployment, and how a release is verified.>
