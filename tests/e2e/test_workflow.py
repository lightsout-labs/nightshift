"""Play a target project through the workflow in a temporary git repository.

Hooks are found through `hooks/hooks.json` and run with the input Claude Code
sends, so the registration is tested together with the hooks.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from conftest import git

ROOT = Path(__file__).resolve().parent.parent.parent
BLOCKED = 2


class Session:
    """A Claude Code session in a project, reduced to the events hooks see."""

    def __init__(self, project: Path):
        self.project = project
        self.registrations = json.loads((ROOT / "hooks" / "hooks.json").read_text())[
            "hooks"
        ]

    def _fire(self, event: str, tool: str | None, payload: dict):
        """Run every hook registered for the event; return the first block."""
        env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(ROOT)}
        payload = {
            "session_id": "e2e",
            "cwd": str(self.project),
            "hook_event_name": event,
            **payload,
        }
        results = []
        for registration in self.registrations.get(event, []):
            matcher = registration.get("matcher")
            if tool and matcher and not re.fullmatch(matcher, tool):
                continue
            for hook in registration["hooks"]:
                results.append(
                    subprocess.run(
                        hook["command"],
                        shell=True,
                        cwd=self.project,
                        env=env,
                        input=json.dumps(payload),
                        capture_output=True,
                        text=True,
                    )
                )
        assert results, f"no hook is registered for {event} {tool or ''}"
        blocks = [result for result in results if result.returncode != 0]
        return blocks[0] if blocks else results[0]

    def tool(self, name: str, **tool_input):
        return self._fire(
            "PreToolUse", name, {"tool_name": name, "tool_input": tool_input}
        )

    def human_says(self, prompt: str):
        return self._fire("UserPromptSubmit", None, {"prompt": prompt})

    def gate(self, *documents: str):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "nightshift.py"),
                "gate",
                *documents,
            ],
            cwd=self.project,
            capture_output=True,
            text=True,
        )


def write_requirements_draft(project: Path) -> Path:
    """What the `spec` skill leaves behind when it stops at the gate."""
    template = (ROOT / "templates" / "requirements.md").read_text()
    requirements = project / "docs" / "requirements.md"
    requirements.parent.mkdir()
    requirements.write_text(template)
    (project / ".nightshift").touch()
    git(project, "switch", "--quiet", "-c", "docs/requirements")
    git(project, "add", "--all")
    git(project, "commit", "--quiet", "-m", "docs: draft requirements")
    return requirements


def test_requirements_gate(repository):
    session = Session(repository)
    requirements = write_requirements_draft(repository)
    path = "docs/requirements.md"

    # Draft: the gate is closed.
    closed = session.gate(path)
    assert closed.returncode == 1
    assert f"{path} (Draft)" in closed.stderr

    # The agent cannot approve, by any tool.
    by_edit = session.tool(
        "Edit",
        file_path=str(requirements),
        old_string="Status: Draft",
        new_string="Status: Approved",
    )
    by_write = session.tool(
        "Write",
        file_path=str(requirements),
        content=requirements.read_text().replace("Draft", "Approved", 1),
    )
    by_shell = session.tool(
        "Bash", command=f"sed -i 's/Status: Draft/Status: Approved/' {path}"
    )
    by_posing_as_the_human = session.tool("Bash", command="claude -p approve")
    for attempt in (by_edit, by_write, by_shell, by_posing_as_the_human):
        assert attempt.returncode == BLOCKED
        assert attempt.stderr
    assert session.gate(path).returncode == 1

    # Ordinary work on the draft is allowed.
    assert session.tool("Bash", command="git status").returncode == 0

    # Feedback from the human is not approval.
    feedback = session.human_says("approve once section 2 is clearer")
    assert feedback.returncode == 0
    assert session.gate(path).returncode == 1

    # The human approves: the gate opens and the change is ready to commit.
    approval = session.human_says("approve")
    assert approval.returncode == 0
    assert path in approval.stdout
    assert session.gate(path).returncode == 0
    assert git(repository, "status", "--porcelain").split() == ["M", path]


def test_hooks_do_nothing_in_a_repository_without_the_marker(repository):
    session = Session(repository)
    document = repository / "docs" / "requirements.md"
    document.parent.mkdir()
    document.write_text("# Requirements\n\nStatus: Draft\n")

    edit = session.tool(
        "Edit",
        file_path=str(document),
        old_string="Status: Draft",
        new_string="Status: Approved",
    )
    shell = session.tool("Bash", command="claude -p approve")
    prompt = session.human_says("approve")

    assert edit.returncode == 0
    assert shell.returncode == 0
    assert prompt.returncode == 0
    assert prompt.stdout == ""
    assert "Status: Draft" in document.read_text()


def test_main_protection(repository):
    session = Session(repository)
    write_requirements_draft(repository)
    git(repository, "switch", "--quiet", "-c", "main")

    def shell(command: str):
        return session.tool("Bash", command=command)

    # On `main`, the agent can neither commit nor push.
    for command in ("git commit -am 'feat: a change'", "git push"):
        blocked = shell(command)
        assert blocked.returncode == BLOCKED
        assert "main" in blocked.stderr

    # Starting a branch and committing on it in one command is the way out.
    assert shell("git switch -c feat/a && git commit -am x").returncode == 0

    # On a branch, commits and pushes of that branch are allowed.
    git(repository, "switch", "--quiet", "-c", "feat/a")
    for command in ("git commit -am 'feat: a change'", "git push -u origin feat/a"):
        assert shell(command).returncode == 0

    # From a branch, `main` still cannot be pushed to, and nothing is forced.
    for command in ("git push origin feat/a:main", "git push --force origin feat/a"):
        blocked = shell(command)
        assert blocked.returncode == BLOCKED
        assert blocked.stderr


def test_main_protection_does_nothing_without_the_marker(repository):
    session = Session(repository)

    for command in ("git commit -m x", "git push --force origin main"):
        assert session.tool("Bash", command=command).returncode == 0
