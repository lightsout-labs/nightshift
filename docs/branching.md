# Branch strategy

Trunk-based development with short-lived branches. `main` is the only
long-lived branch and is always releasable.

## Rules

- Every change lands on `main` through a pull request. Direct pushes, force
  pushes, and deletion of `main` are blocked by branch protection, for
  administrators too.
- One branch and one pull request per change. Branch from the latest `main`.
- Pull requests are squash-merged, so `main` has a linear history with one
  commit per change. The branch is deleted on merge.
- Keep branches short-lived: hours to a couple of days. Rebase on `main` rather
  than merging `main` into the branch.
- No approving review is required. The project has a single maintainer, and the
  human gates are the document approvals, not code review.
- Once CI exists, its checks are required before merging, and pull requests
  auto-merge when they are green.

The only exception was the bootstrap commit that introduced this document,
pushed directly to `main` before protection was enabled.

## Branch names

`<type>/<short-kebab-description>`, for example `feat/spec-skill`.

| Type | Use |
|---|---|
| `feat` | New skill, template, script, or behavior |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `chore` | Tooling, CI, repository maintenance |
| `refactor` | Restructuring without behavior change |

## Commits and pull request titles

The pull request title becomes the squashed commit on `main`. Write it as a
[Conventional Commit](https://www.conventionalcommits.org/):
`<type>: <imperative summary>`, using the types above. Commits inside a branch
are not preserved and need no particular format.

## Releases

Releases are tags on `main` of the form `vMAJOR.MINOR.PATCH`. There are no
release or maintenance branches.
