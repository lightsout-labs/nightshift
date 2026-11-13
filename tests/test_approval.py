"""Approval hook: the human approves the waiting documents with one word."""

import pytest
from conftest import run_hook, write_doc


def prompt(project, text):
    return run_hook(
        "approval",
        {
            "hook_event_name": "UserPromptSubmit",
            "cwd": str(project),
            "prompt": text,
        },
    )


@pytest.mark.parametrize("word", ["approve", "approved", "  Approve\n"])
def test_approves_every_draft_gated_document_and_reports_them(project, word):
    requirements = write_doc(project, "docs/requirements.md", "Approved")
    architecture = write_doc(project, "docs/architecture.md", "Draft")
    backlog = write_doc(project, "docs/backlog.md", "Draft")
    delivery = write_doc(project, "docs/delivery/v1.0.0.md", "Draft")
    before = requirements.read_text()

    result = prompt(project, word)

    assert result.returncode == 0
    for doc in (architecture, backlog, delivery):
        assert doc.read_text() == "# Title\n\nStatus: Approved\n\nBody text.\n"
    assert requirements.read_text() == before
    assert "docs/architecture.md" in result.stdout
    assert "docs/backlog.md" in result.stdout
    assert "docs/delivery/v1.0.0.md" in result.stdout
    assert "docs/requirements.md" not in result.stdout


def test_approval_leaves_slice_statuses_and_other_documents_alone(project):
    backlog = project / "docs" / "backlog.md"
    backlog.write_text("# Backlog\n\nStatus: Draft\n\n## S01: First\n\nStatus: Draft\n")
    adr = write_doc(project, "docs/adr/0001-choice.md", "Draft")

    prompt(project, "approve")

    assert backlog.read_text() == (
        "# Backlog\n\nStatus: Approved\n\n## S01: First\n\nStatus: Draft\n"
    )
    assert "Status: Draft" in adr.read_text()


@pytest.mark.parametrize(
    "text", ["approve, but rename section 2", "I do not approve", "looks good"]
)
def test_any_other_prompt_changes_nothing(project, text):
    doc = write_doc(project, "docs/requirements.md", "Draft")

    result = prompt(project, text)

    assert result.returncode == 0
    assert result.stdout == ""
    assert "Status: Draft" in doc.read_text()


def test_approve_with_nothing_waiting_tells_the_agent(project):
    write_doc(project, "docs/requirements.md", "Approved")

    result = prompt(project, "approve")

    assert result.returncode == 0
    assert "No document" in result.stdout


def test_does_nothing_without_the_marker(tmp_path):
    doc = write_doc(tmp_path, "docs/requirements.md", "Draft")

    result = prompt(tmp_path, "approve")

    assert result.returncode == 0
    assert result.stdout == ""
    assert "Status: Draft" in doc.read_text()
