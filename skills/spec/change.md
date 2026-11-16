# spec: change a project under way

The requirements are approved and a backlog exists, so the human is adding to
or changing what gets built. Handle the whole change on one branch, behind one
gate. Write everything in English. Do the work yourself; do not launch agents.

1. **Ask** about the change only, as step 2 of the spec skill says.
2. **Branch**: create `docs/<short-description>` from the latest `main`.
3. **Requirements**: change or add numbered requirements in
   `docs/requirements.md` and record the answers under Decisions.
4. **Design**: revise `docs/architecture.md`, and add an ADR, only where the
   change needs a different design. Follow step 2 of
   `${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md`.
5. **Slices**: add slices for the change to `docs/backlog.md`, following
   step 2 of `${CLAUDE_PLUGIN_ROOT}/skills/slice/SKILL.md`. Change a slice
   that is not `Done` rather than adding one, where that is simpler.
6. **Reopen the gate**: set every document you changed to `Status: Draft`,
   with the Edit tool.
7. Commit with the message `docs: <summary of the change>`, push, and open a
   pull request with the same title. Print the paths of the changed
   documents, a summary of the change in at most five lines, and: "Read the
   changes. Reply with changes, or type `approve`." Stop.

On changes, apply them, push, and stop again. On `approve`, a hook sets the
status: commit it, push, squash-merge, switch to the updated `main`, and tell
the human to run `/clear` and then `/nightshift:build`.
