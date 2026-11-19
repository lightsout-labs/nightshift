---
name: spec
description: Start a nightshift project, or change the requirements of one under way. Asks clarifying questions, writes docs/requirements.md as a draft, and stops for the human's approval.
disable-model-invocation: true
---

# spec: agree on the requirements

Turn the human's idea into `docs/requirements.md` and stop at the
requirements gate. Do the work yourself; do not launch agents. Write
documents in the project's `language` (step 2; `NS config` prints it once
`.nightshift` exists). `NS` is
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/nightshift.py"`, run from the
project root.

## 1. Understand

Read what the human gave you: the arguments to this command, the GitHub
issues they name (`gh issue view <n>`), any notes file they point to, and an existing `docs/requirements.md` if there is one (then
you are revising it, not starting over). If it is `Approved` and
`docs/backlog.md` exists, follow `${CLAUDE_PLUGIN_ROOT}/skills/spec/change.md`
instead of the steps below.

## 2. Ask

Ask clarifying questions until no requirement is ambiguous. Use the
AskUserQuestion tool, a few questions per round, each with concrete options
and your recommendation first.

- Ask only what changes what gets built or how it is accepted: users and
  main flows, scope limits, platforms, data, quality bars, deployment.
- Propose what would make the product better and the human has not
  mentioned, such as a feature or a more polished UI, as options to accept
  or decline. This is where ambition is agreed; later stages build exactly
  what was agreed.
- Make each quality bar observable: a reference product, or named behaviors.
- Ask which license the project has, unless a `LICENSE` file exists.
- Unless `.nightshift` exists, ask in the first round for the project's
  settings: the language of its documents (English first); whether CI runs
  the checks, or the local `make check` and `make e2e` are enough to merge;
  and whether `build` stops after each slice, so the human can `/clear`, or
  builds every slice in one run; then also at what context size, in tokens,
  Claude Code compacts it (200000 first).
- Do not ask what you can decide yourself or what belongs to design.
- Stop asking when further answers would not change the document.

## 3. Write

1. Copy `${CLAUDE_PLUGIN_ROOT}/templates/requirements.md` to
   `docs/requirements.md` and fill in every section. Keep `Status: Draft`.
   Each requirement is one numbered, testable statement. If something
   seems missing, ask; add nothing the human has not agreed to. Record the
   human's answers under Decisions.
2. Unless it exists, copy `${CLAUDE_PLUGIN_ROOT}/templates/nightshift` to
   `.nightshift` in the project root, set the human's answers in it, and
   run `NS config` to check it. The file turns the plugin's hooks on.
3. Write the repository's documents, where they do not exist yet:
   - `LICENSE`: the full text of the chosen license, with this year and
     `git config user.name` as the holder. No file if the human wants none.
   - `README.md`: the project's name, the goal in one or two sentences, and
     a link to `docs/requirements.md`. Keep what an existing one says.
   - `.claude/settings.json`: a copy of
     `${CLAUDE_PLUGIN_ROOT}/templates/settings.json`, which loads this
     plugin in every session in the project. Add its keys to an existing
     file instead. With `stop-after-slice: no`, also set
     `env.CLAUDE_CODE_AUTO_COMPACT_WINDOW` to the chosen size.

## 4. Open the gate

1. If the directory is not a git repository, run `git init`.
2. Create the branch `docs/requirements`, commit these files with the message
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
