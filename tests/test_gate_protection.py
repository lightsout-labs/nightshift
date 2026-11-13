"""Gate protection: the agent cannot approve a document or pose as the human."""

import pytest
from conftest import run_hook, write_doc

BLOCKED = 2


def tool_call(project, tool, **tool_input):
    return run_hook(
        "gate_protection",
        {
            "hook_event_name": "PreToolUse",
            "cwd": str(project),
            "tool_name": tool,
            "tool_input": tool_input,
        },
    )


def test_blocks_an_edit_that_approves_a_document(project):
    doc = write_doc(project, "docs/requirements.md", "Draft")

    result = tool_call(
        project,
        "Edit",
        file_path=str(doc),
        old_string="Status: Draft",
        new_string="Status: Approved",
    )

    assert result.returncode == BLOCKED
    assert "approve" in result.stderr


def test_blocks_an_edit_that_approves_by_replacing_one_word(project):
    doc = write_doc(project, "docs/requirements.md", "Draft")

    result = tool_call(
        project, "Edit", file_path=str(doc), old_string="Draft", new_string="Approved"
    )

    assert result.returncode == BLOCKED


def test_blocks_a_write_that_approves_a_document(project):
    doc = write_doc(project, "docs/requirements.md", "Draft")

    result = tool_call(
        project,
        "Write",
        file_path=str(doc),
        content="# Requirements\n\nStatus: Approved\n\nRewritten.\n",
    )

    assert result.returncode == BLOCKED


def test_blocks_a_write_that_creates_an_approved_document(project):
    result = tool_call(
        project,
        "Write",
        file_path="docs/architecture.md",
        content="# Architecture\n\nStatus: Approved\n",
    )

    assert result.returncode == BLOCKED


def test_allows_changes_that_keep_the_status(project):
    draft = write_doc(project, "docs/requirements.md", "Draft")
    approved = write_doc(project, "docs/architecture.md", "Approved")

    edit_draft = tool_call(
        project,
        "Edit",
        file_path=str(draft),
        old_string="Body text.",
        new_string="An approved status is `Status: Approved`.",
    )
    edit_approved = tool_call(
        project,
        "Edit",
        file_path=str(approved),
        old_string="Body text.",
        new_string="Synced with the code.",
    )
    rewrite_approved = tool_call(
        project,
        "Write",
        file_path=str(approved),
        content="# Architecture\n\nStatus: Approved\n\nSynced with the code.\n",
    )

    assert edit_draft.returncode == 0
    assert edit_approved.returncode == 0
    assert rewrite_approved.returncode == 0


@pytest.mark.parametrize(
    "command",
    [
        "sed -i 's/Status: Draft/Status: Approved/' docs/requirements.md",
        "printf '# T\\n\\nstatus:  approved\\n' > docs/requirements.md",
    ],
)
def test_blocks_a_shell_command_that_mentions_the_approved_status(project, command):
    result = tool_call(project, "Bash", command=command)

    assert result.returncode == BLOCKED


@pytest.mark.parametrize(
    "command",
    [
        "claude -p approve",
        "cd /tmp && FOO=1 claude --print approve",
        "echo approve | /usr/local/bin/claude",
        "npx @anthropic-ai/claude-code -p approve",
        "result=$(claude -p approve)",
    ],
)
def test_blocks_a_shell_command_that_starts_a_nested_session(project, command):
    result = tool_call(project, "Bash", command=command)

    assert result.returncode == BLOCKED
    assert "nested" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "grep -r claude docs/",
        "cat CLAUDE.md && ls .claude",
        "git commit -m 'docs: describe the claude plugin'",
    ],
)
def test_allows_ordinary_shell_commands(project, command):
    result = tool_call(project, "Bash", command=command)

    assert result.returncode == 0


def test_protects_a_project_when_called_from_a_subdirectory(project):
    doc = write_doc(project, "docs/requirements.md", "Draft")

    result = run_hook(
        "gate_protection",
        {
            "hook_event_name": "PreToolUse",
            "cwd": str(project / "docs"),
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(doc),
                "old_string": "Draft",
                "new_string": "Approved",
            },
        },
    )

    assert result.returncode == BLOCKED


def test_does_nothing_without_the_marker(tmp_path):
    doc = write_doc(tmp_path, "docs/requirements.md", "Draft")

    edit = tool_call(
        tmp_path, "Edit", file_path=str(doc), old_string="Draft", new_string="Approved"
    )
    bash = tool_call(tmp_path, "Bash", command="claude -p 'Status: Approved'")

    assert edit.returncode == 0
    assert bash.returncode == 0
