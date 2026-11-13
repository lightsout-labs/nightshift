"""`check-docs.py`: are a project's documents consistent with each other?"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ROOT, run_check_docs

FENCE = "```"

REQUIREMENTS = """\
# Requirements

Status: Approved

- R1: A sheet can be edited.
"""

# Every kind of link that is not broken: a file, a file with an anchor, a
# directory, an anchor in the same file, a web address, and link syntax that
# is only quoted as code.
ARCHITECTURE = f"""\
# Architecture

Status: Approved

What it must do is in [the requirements](requirements.md#goals). Decisions are
in [adr/](adr/), the first being [storage](adr/0001-storage.md "ADR 1"). See
[Overview](#overview) and [the site](https://example.com/missing.md).

Write a link as `[text](no-such-file.md)`:

{FENCE}markdown
[text](no-such-file.md)
{FENCE}
"""

ADR = """\
# 0001: Storage

Described in [the architecture](../architecture.md).
"""

BACKLOG = """\
# Backlog

Status: Approved

Slices, built in this order.

## S01: Walking skeleton

Status: Done
PR: #1

Acceptance criteria:
- The page loads.

## S02: Edit a cell

Status: In progress

Acceptance criteria:
- A cell can be edited.

Notes:
- Formulas come later.

## S03: Save a sheet

Status: Todo

Acceptance criteria:
- A sheet can be saved.
"""

DELIVERY = """\
# Delivery v1.0.0

Status: Draft

Everything in [the backlog](../backlog.md) was delivered.
"""

DOCUMENTS = {
    "docs/requirements.md": REQUIREMENTS,
    "docs/architecture.md": ARCHITECTURE,
    "docs/adr/0001-storage.md": ADR,
    "docs/backlog.md": BACKLOG,
    "docs/delivery/v1.0.0.md": DELIVERY,
}


@pytest.fixture
def consistent(tmp_path: Path) -> Path:
    """A project whose documents are consistent."""
    for relative, text in DOCUMENTS.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def change(project: Path, relative: str, old: str, new: str) -> None:
    path = project / relative
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new, 1))


def test_passes_silently_on_consistent_documents(consistent):
    result = run_check_docs(cwd=consistent)

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""


def test_passes_before_the_design_exists(tmp_path):
    # After `spec`, a project has only its requirements.
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "requirements.md").write_text(REQUIREMENTS)

    assert run_check_docs(cwd=tmp_path).returncode == 0


@pytest.mark.parametrize(
    ("relative", "old", "new", "reported"),
    [
        pytest.param(
            "docs/architecture.md",
            "Status: Approved\n",
            "",
            ["docs/architecture.md", "Status"],
            id="gated document without a status line",
        ),
        pytest.param(
            "docs/delivery/v1.0.0.md",
            "Status: Draft",
            "Status: Accepted",
            ["docs/delivery/v1.0.0.md", "Status"],
            id="gated document with an unknown status",
        ),
        pytest.param(
            "docs/backlog.md",
            "Status: Todo",
            "Status: Blocked",
            ["docs/backlog.md", "S03", "status"],
            id="slice without a valid status",
        ),
        pytest.param(
            "docs/backlog.md",
            "Acceptance criteria:\n- A sheet can be saved.\n",
            "",
            ["docs/backlog.md", "S03", "acceptance criteria"],
            id="slice without acceptance criteria",
        ),
        pytest.param(
            "docs/backlog.md",
            "## S03: Save a sheet",
            "## Save a sheet",
            ["docs/backlog.md", "Save a sheet", "heading"],
            id="section that is not a slice",
        ),
        pytest.param(
            "docs/backlog.md",
            "## S03:",
            "## S02:",
            ["docs/backlog.md", "S02", "more than once"],
            id="slice number used twice",
        ),
        pytest.param(
            "docs/backlog.md",
            "Status: Todo",
            "Status: In progress",
            ["docs/backlog.md", "S02", "S03", "In progress"],
            id="two slices in progress",
        ),
        pytest.param(
            "docs/backlog.md",
            "PR: #1\n",
            "",
            ["docs/backlog.md", "S01", "pull request"],
            id="done slice without a pull request number",
        ),
        pytest.param(
            "docs/architecture.md",
            "(adr/0001-storage.md ",
            "(adr/0002-storage.md ",
            ["docs/architecture.md:6", "adr/0002-storage.md"],
            id="link to a file that does not exist",
        ),
        pytest.param(
            "docs/adr/0001-storage.md",
            "(../architecture.md)",
            "(architecture.md)",
            ["docs/adr/0001-storage.md:3", "architecture.md"],
            id="link that only resolves from another directory",
        ),
    ],
)
def test_fails_naming_the_file_and_the_reason(consistent, relative, old, new, reported):
    change(consistent, relative, old, new)

    result = run_check_docs(cwd=consistent)

    assert result.returncode == 1
    (line,) = result.stderr.splitlines()
    for text in reported:
        assert text in line


def test_reports_every_problem_in_one_run(consistent):
    change(consistent, "docs/requirements.md", "Status: Approved\n", "")
    change(consistent, "docs/backlog.md", "PR: #1\n", "")
    change(consistent, "docs/delivery/v1.0.0.md", "../backlog.md", "backlog.md")

    result = run_check_docs(cwd=consistent)

    assert result.returncode == 1
    files = [line.split(":")[0] for line in result.stderr.splitlines()]
    assert files == [
        "docs/backlog.md",
        "docs/delivery/v1.0.0.md",
        "docs/requirements.md",
    ]


def test_fails_when_there_is_no_docs_directory(tmp_path):
    result = run_check_docs(cwd=tmp_path)

    assert result.returncode == 1
    assert "project root" in result.stderr


def test_runs_as_a_single_copied_file_and_reports_its_version(consistent):
    # `build` copies the file into the project, where neither the plugin nor
    # any installed package is available to it.
    copy = consistent / "scripts" / "check-docs.py"
    copy.parent.mkdir()
    shutil.copy(ROOT / "templates" / "check-docs.py", copy)

    def run(*arguments: str):
        return subprocess.run(
            [sys.executable, "-I", "-S", "scripts/check-docs.py", *arguments],
            cwd=consistent,
            capture_output=True,
            text=True,
        )

    assert run().returncode == 0
    assert run("--version").stdout.strip().isdigit()
