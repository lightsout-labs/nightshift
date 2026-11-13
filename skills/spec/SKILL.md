---
name: spec
description: Start a nightshift project. Asks clarifying questions, writes docs/requirements.md as a draft, and stops for the human's approval.
disable-model-invocation: true
---

# spec: agree on the requirements

Turn the human's idea into `docs/requirements.md` and stop at the
requirements gate. Write everything in English. Do the work yourself; do not
launch agents.

## 1. Understand

Read what the human gave you: the arguments to this command, any notes file
they point to, and an existing `docs/requirements.md` if there is one (then
you are revising it, not starting over).

## 2. Ask

Ask clarifying questions until no requirement is ambiguous. Use the
AskUserQuestion tool, a few questions per round, each with concrete options
and your recommendation first.

- Ask only what changes what gets built or how it is accepted: users and
  main flows, scope limits, platforms, data, quality bars, deployment.
- Do not ask what you can decide yourself or what belongs to design.
- Stop asking when further answers would not change the document.

## 3. Write

1. Copy `${CLAUDE_PLUGIN_ROOT}/templates/requirements.md` to
   `docs/requirements.md` and fill in every section. Keep `Status: Draft`.
   Each requirement is one numbered, testable statement. Record the human's
   answers under Decisions.
2. Create the empty marker file `.nightshift` in the project root. It turns
   the plugin's hooks on for this project.

## 4. Open the gate

1. If the directory is not a git repository, run `git init`.
2. Create the branch `docs/requirements`, commit both files with the message
   `docs: draft requirements`, and push.
3. Open a pull request with the same title. If there is no remote or `gh`
   fails, say so and carry on without one.
4. Print the path of the document, a summary of at most five lines, and:
   "Read `docs/requirements.md`. Reply with changes, or type `approve`."
5. Stop.

You cannot approve the document yourself, and a hook blocks the attempt.

## 5. After the human replies

- **Changes**: apply them, commit, push, print what changed, and stop again.
- **`approve`**: a hook sets the status and tells you. Commit the change with
  the message `docs: approve requirements`, push, squash-merge the pull
  request, and switch to the updated `main`. With no pull request,
  fast-forward `main` to the branch instead. Then, without waiting for the
  human, read `${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md` and follow it in
  this session; the human's answers are useful context for the design.
