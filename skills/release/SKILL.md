---
name: release
description: Release a nightshift project once every slice is done. Tags a version, writes the changelog, deploys, writes the delivery report as a draft, and stops for the human's acceptance.
disable-model-invocation: true
---

# release: deliver a version

Release what the backlog holds and stop at the acceptance gate. Write
everything in English. Do the work yourself; do not launch agents. `PLUGIN`
below is `${CLAUDE_PLUGIN_ROOT}`, `NS` is
`python3 "PLUGIN/scripts/nightshift.py"` run from the project root, and
`vX.Y.Z` is the version. The skill needs a GitHub remote and `gh`.

## 1. Find the release

1. Run `NS gate docs/architecture.md docs/backlog.md`. If it fails, tell the
   human what it printed, and stop.
2. If a branch `docs/delivery-vX.Y.Z`, local or remote, holds a report that
   is `Status: Draft`, that release waits: switch to it and go to step 4.3.
3. Run `NS next`.
   - It prints a slice: tell the human that slice is not done and that
     `/nightshift:build` comes first, and stop.
   - The backlog has no slices: if the newest `docs/backlog/vX.Y.Z.md` has no
     `docs/delivery/vX.Y.Z.md`, an earlier run stopped midway; carry on with
     that version at step 3, skipping what is done. Otherwise tell the human
     there is nothing to release and `/nightshift:spec` starts the next, and stop.
4. Choose the version: `v0.1.0` with no `v*` tag. Otherwise raise the latest
   tag's minor number, its patch number when every slice is a fix, or its
   major number only when the requirements say compatibility breaks.

## 2. Changelog and archive

1. Create the branch `chore/release-vX.Y.Z` from the latest `main`.
2. In `CHANGELOG.md`, which starts with `# Changelog`, add
   `## vX.Y.Z - <date>` above the earlier versions: one line per slice, in
   the user's terms, with its pull request number.
3. If the project records its version in a file, set it there.
4. Run `NS archive vX.Y.Z`. It moves the slices to `docs/backlog/vX.Y.Z.md`
   and refuses while one is not `Done`. Fix any link that the move broke.
5. Run `make check` and `make e2e`. Commit with the message
   `chore: release vX.Y.Z`, push, open a pull request with the same title,
   and run `gh pr merge --squash --auto`, then `gh pr checks --watch`. When
   it has merged, switch to the updated `main`.

## 3. Tag and deploy

1. Run `git tag vX.Y.Z` and `git push origin vX.Y.Z`.
2. Deploy as the Deployment section of `docs/architecture.md` describes, and
   verify the result the way it says.
3. Fix a failed deployment through a pull request of its own. Never move a
   tag: tag and deploy the fix as the next patch version, and name it in the
   report. After three failed fixes of one problem, ask the human and stop.

## 4. Delivery report

1. Create the branch `docs/delivery-vX.Y.Z` from `main`. Copy
   `PLUGIN/templates/delivery.md` to `docs/delivery/vX.Y.Z.md` and fill in
   every section. Keep `Status: Draft`.
   - **Delivered**: every requirement by number, with the slices that
     deliver it. Claim only what a test proves or you tried on the deployed
     version; say plainly what is missing.
   - **How to try it**: steps you have followed yourself.
   - **Known limits**: also the criteria marked as not yet verified.
2. Run `make check`. Commit as `docs: delivery report vX.Y.Z`, push, and
   open a pull request with the same title.
3. Print the path, a summary of at most five lines, where to try the
   delivery, and: "Try it and read `docs/delivery/vX.Y.Z.md`. Reply with
   changes, or type `approve` to accept the delivery." Stop. You cannot
   accept it yourself, and a hook blocks the attempt.

## 5. After the human replies

- **Changes**: apply those to the report, commit, push, and stop again. A
  change to the product belongs to the next release: record it under Known
  limits and say so.
- **`approve`**: a hook sets the status and tells you. Commit the change with
  the message `docs: accept vX.Y.Z`, push, squash-merge the pull request,
  and switch to the updated `main`. Tell the human: "vX.Y.Z is accepted and
  the release is closed. `/nightshift:spec` starts the next one." Stop.
