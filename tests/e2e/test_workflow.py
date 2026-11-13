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

    def stops(self):
        """The agent finishes its turn."""
        return self._fire("Stop", None, {"stop_hook_active": False})

    def script(self, *arguments: str):
        """Run `nightshift.py` the way a skill does, from the project root."""
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "nightshift.py"), *arguments],
            cwd=self.project,
            capture_output=True,
            text=True,
        )

    def gate(self, *documents: str):
        return self.script("gate", *documents)

    def check_docs(self):
        """Run the document check the way the project's `make check` does."""
        return subprocess.run(
            [sys.executable, str(ROOT / "templates" / "check-docs.py")],
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


def write_design_draft(project: Path) -> list[str]:
    """What the `design` skill leaves behind when it stops at the gate."""
    copies = {
        "architecture.md": "docs/architecture.md",
        "adr.md": "docs/adr/0001-first-decision.md",
        "backlog.md": "docs/backlog.md",
    }
    for template, relative in copies.items():
        target = project / relative
        target.parent.mkdir(exist_ok=True)
        target.write_text((ROOT / "templates" / template).read_text())
    git(project, "switch", "--quiet", "-c", "docs/design")
    git(project, "add", "--all")
    git(project, "commit", "--quiet", "-m", "docs: draft design")
    return ["docs/architecture.md", "docs/backlog.md"]


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


def test_design_gate(repository):
    session = Session(repository)
    write_requirements_draft(repository)
    requirements = "docs/requirements.md"

    # `design` refuses to start before the requirements are approved.
    assert session.gate(requirements).returncode == 1
    session.human_says("approve")
    git(repository, "commit", "--quiet", "-am", "docs: approve requirements")
    assert session.gate(requirements).returncode == 0

    # The design is drafted from the templates: `build` cannot start yet.
    design = write_design_draft(repository)
    closed = session.gate(*design)
    assert closed.returncode == 1
    for path in design:
        assert f"{path} (Draft)" in closed.stderr

    # The drafts are consistent, so the project's `make check` can pass.
    consistent = session.check_docs()
    assert consistent.returncode == 0, consistent.stderr

    # The agent cannot approve its own design.
    blocked = session.tool(
        "Edit",
        file_path=str(repository / "docs" / "backlog.md"),
        old_string="Status: Draft",
        new_string="Status: Approved",
    )
    assert blocked.returncode == BLOCKED
    assert session.gate(*design).returncode == 1

    # One word from the human approves the architecture and the backlog
    # together, and leaves the ADR and the slice statuses alone.
    approval = session.human_says("approve")
    for path in design:
        assert path in approval.stdout
    assert session.gate(*design).returncode == 0
    assert sorted(git(repository, "status", "--porcelain").split()) == sorted(
        ["M", "M", *design]
    )

    # The approved backlog is ready for `build`: the walking skeleton is
    # next, and only one slice at a time can be in progress.
    assert session.script("next").stdout.startswith("## S01: Walking skeleton")
    assert session.script("set-status", "S01", "In progress").returncode == 0
    assert session.script("set-status", "S02", "In progress").returncode == 1
    assert session.script("set-status", "S01", "Done").returncode == 0
    assert session.script("next").stdout.startswith("## S02: ")
    assert session.gate(*design).returncode == 0

    # A finished slice must record its pull request before `make check`
    # passes again.
    unrecorded = session.check_docs()
    assert unrecorded.returncode == 1
    assert "docs/backlog.md: S01" in unrecorded.stderr
    backlog = repository / "docs" / "backlog.md"
    backlog.write_text(
        backlog.read_text().replace("Status: Done\n", "Status: Done\nPR: #1\n")
    )
    assert session.check_docs().returncode == 0


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


def test_check_before_stopping(repository):
    session = Session(repository)
    write_requirements_draft(repository)
    session.human_says("approve")
    write_design_draft(repository)
    session.human_says("approve")
    # The project's `make check`: the document check and one project rule.
    (repository / "Makefile").write_text(
        "check:\n"
        f'\t@"{sys.executable}" "{ROOT / "templates" / "check-docs.py"}"\n'
        "\t@test ! -f failing-test || (echo 'test_cell failed'; exit 1)\n"
    )
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "-m", "docs: approve design")
    failing_test = repository / "failing-test"

    # Between slices, the agent stops freely, whatever the state of the code.
    failing_test.touch()
    assert session.stops().returncode == 0

    # While a slice is being built, it cannot stop on a failing check.
    session.script("set-status", "S01", "in-progress")
    blocked = session.stops()
    assert blocked.returncode == BLOCKED
    assert "test_cell failed" in blocked.stderr

    # The document check is part of it: a finished slice with no pull request
    # number would fail, but by then no slice is in progress.
    failing_test.unlink()
    assert session.stops().returncode == 0

    # None of this shows up in the project's working tree.
    status = git(repository, "status", "--porcelain").split()
    assert status == ["M", "docs/backlog.md"]


def test_acceptance_gate(repository):
    session = Session(repository)
    write_requirements_draft(repository)
    session.human_says("approve")
    write_design_draft(repository)
    session.human_says("approve")
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "-m", "docs: approve design")
    version = "v0.1.0"
    backlog = repository / "docs" / "backlog.md"

    # `release` refuses while a slice is not done, and archives nothing.
    session.script("set-status", "S01", "done")
    refused = session.script("archive", version)
    assert refused.returncode == 1
    assert "S02" in refused.stderr
    assert "## S01" in backlog.read_text()

    # Every slice is built: the release moves them out of the backlog, which
    # stays approved and consistent with no slices in it.
    session.script("set-status", "S02", "done")
    backlog.write_text(
        backlog.read_text().replace("Status: Done\n", "Status: Done\nPR: #1\n")
    )
    assert "No slice is left" in session.script("next").stdout
    assert session.script("archive", version).returncode == 0
    archive = repository / "docs" / "backlog" / f"{version}.md"
    assert "## S01" in archive.read_text()
    assert "## S02" in archive.read_text()
    assert "## S" not in backlog.read_text()
    assert "has no slices" in session.script("next").stdout
    assert session.gate("docs/architecture.md", "docs/backlog.md").returncode == 0
    assert session.check_docs().returncode == 0

    # The version is tagged on `main`, where the agent still cannot commit.
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "-m", f"chore: release {version}")
    git(repository, "switch", "--quiet", "-c", "main")
    tagging = session.tool(
        "Bash", command=f"git tag {version} && git push origin {version}"
    )
    assert tagging.returncode == 0

    # The delivery report is drafted from the template: not accepted yet.
    git(repository, "switch", "--quiet", "-c", f"docs/delivery-{version}")
    path = f"docs/delivery/{version}.md"
    report = repository / path
    report.parent.mkdir()
    template = (ROOT / "templates" / "delivery.md").read_text()
    report.write_text(template.replace("vX.Y.Z", version))
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "-m", f"docs: delivery report {version}")
    closed = session.gate(path)
    assert closed.returncode == 1
    assert f"{path} (Draft)" in closed.stderr
    consistent = session.check_docs()
    assert consistent.returncode == 0, consistent.stderr

    # The agent cannot accept its own delivery.
    by_edit = session.tool(
        "Edit",
        file_path=str(report),
        old_string="Status: Draft",
        new_string="Status: Approved",
    )
    by_shell = session.tool(
        "Bash", command=f"sed -i 's/Status: Draft/Status: Approved/' {path}"
    )
    for attempt in (by_edit, by_shell):
        assert attempt.returncode == BLOCKED
    assert session.gate(path).returncode == 1

    # One word from the human accepts it, and changes nothing else.
    acceptance = session.human_says("approve")
    assert path in acceptance.stdout
    assert session.gate(path).returncode == 0
    assert git(repository, "status", "--porcelain").split() == ["M", path]
