"""`nightshift.py gate`: is every named document approved?"""

from conftest import run_script, write_doc


def test_gate_opens_when_every_document_is_approved(project):
    write_doc(project, "docs/requirements.md", "Approved")
    write_doc(project, "docs/architecture.md", "Approved")

    result = run_script(
        "gate", "docs/requirements.md", "docs/architecture.md", cwd=project
    )

    assert result.returncode == 0


def test_gate_names_only_the_documents_that_are_not_approved(project):
    write_doc(project, "docs/requirements.md", "Approved")
    write_doc(project, "docs/architecture.md", "Draft")
    write_doc(project, "docs/backlog.md", None)

    result = run_script(
        "gate",
        "docs/requirements.md",
        "docs/architecture.md",
        "docs/backlog.md",
        "docs/missing.md",
        cwd=project,
    )

    assert result.returncode == 1
    assert "docs/requirements.md" not in result.stderr
    assert "docs/architecture.md (Draft)" in result.stderr
    assert "docs/backlog.md (no status)" in result.stderr
    assert "docs/missing.md (missing)" in result.stderr


def test_only_the_line_after_the_title_is_the_document_status(project):
    # A backlog carries slice statuses and may quote an approved status in
    # its body; neither approves the document.
    (project / "docs" / "backlog.md").write_text(
        "# Backlog\n\nStatus: Draft\n\n## S01: First\n\nStatus: Done\n\n"
        "Status: Approved\n"
    )

    result = run_script("gate", "docs/backlog.md", cwd=project)

    assert result.returncode == 1
    assert "docs/backlog.md (Draft)" in result.stderr
