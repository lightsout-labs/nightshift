---
name: fix
description: Turn GitHub issues that report defects into fix slices at the front of a nightshift project's backlog, and name the issues that ask for something new for spec. No gate; build fixes them.
disable-model-invocation: true
---

# fix: plan the fixes for reported defects

Add a fix slice to `docs/backlog.md` for each issue that reports a defect,
merge it, and stop. Do the work yourself; do not launch agents. `NS` below
is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/nightshift.py"`, run from the
project root. Run `NS config` and write in its `language`. The skill needs a
GitHub remote and `gh`.

## 1. Read the issues

1. Run `NS gate docs/requirements.md docs/architecture.md docs/backlog.md`.
   If it fails, tell the human what it printed, and stop.
2. Read each issue named in the arguments with `gh issue view <n>`, or every
   open issue (`gh issue list --state open`) when none is named. Skip an
   issue that a slice of `docs/backlog.md` names in its `Fixes` or `Closes`
   line.
3. Read `docs/requirements.md` and `docs/architecture.md`.

## 2. Sort them

Each issue is one of:

- **Defect**: the product does not do what an approved requirement, or the
  architecture, says it does. A requirement that promises behavior "as in"
  another product covers that product's behavior. Read the code only to
  settle a doubt, not to fix it.
- **Change**: it asks for something no requirement states. It belongs to
  `/nightshift:spec`, which goes through the requirements gate. An issue
  that is partly both is split: the defect here, the rest left to `spec`.
- **Not a problem**: the product already behaves as the issue asks, or the
  requirements rule the behavior out.

If you cannot tell which, ask the human with AskUserQuestion, giving the
requirement you weighed and your recommendation first. Decide the rest.

## 3. Write the fix slices

Defects do not change what was agreed, so they need no gate.

1. Create the branch `docs/fix-<issue numbers joined by ->` from the latest
   `main`.
2. Write one slice for each defect, or one for several defects with the same
   cause. Number them after the highest number in the backlog and in the
   files under `docs/backlog/`, and place them before the first slice that
   is `Todo`, or at the end, so that they are built next:

   ```markdown
   ## Snn: Fix <the behavior, in the user's terms>

   Status: Todo
   Fixes: #40, #44

   Acceptance criteria:
   - <The issue's steps give the correct result.> (R12)
   ```

   The criteria say what correct looks like, observably, and end with the
   requirement they restore; the first one is the issue's own report. Name
   every case the issue lists, and the same fault elsewhere when the issue
   asks to check further. Nothing beyond restoring the requirement.
3. Run `NS next` and `make check`. Commit with the message
   `docs: plan fixes for #40, #44`, push, open a pull request with the same
   title, and merge it: with `ci: yes`, `gh pr merge --squash --auto`, then
   `gh pr checks --watch`; with `ci: no`, `gh pr merge --squash`. When it
   has merged, switch to the updated `main`.

With no defect, skip this step.

## 4. Report

Tell the human, at most one line each:

- each fix slice and the issues it fixes;
- each change, and that `/nightshift:spec #<n>` handles it;
- each issue that is not a problem, and why. Do not close it; that is the
  human's call.

Then: "Run `/clear`, then `/nightshift:build`." if a fix slice was added.
Stop.
