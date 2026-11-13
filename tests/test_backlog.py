"""`nightshift.py next` and `set-status`: progress through the backlog."""

import pytest
from conftest import run_script

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

Status: Todo

Acceptance criteria:
- A cell can be edited.

Notes:
- Formulas come later.

## S03: Save a sheet

Status: Todo

Acceptance criteria:
- A sheet can be saved.
"""


@pytest.fixture
def backlog(project):
    path = project / "docs" / "backlog.md"
    path.write_text(BACKLOG)
    return path


def test_next_prints_the_whole_section_of_the_first_slice_that_is_not_done(backlog):
    result = run_script("next", cwd=backlog.parent.parent)

    assert result.returncode == 0
    assert result.stdout == (
        "## S02: Edit a cell\n\nStatus: Todo\n\nAcceptance criteria:\n"
        "- A cell can be edited.\n\nNotes:\n- Formulas come later.\n"
    )


def test_next_reports_that_no_slice_is_left(backlog):
    backlog.write_text(BACKLOG.replace("Status: Todo", "Status: Done"))

    result = run_script("next", cwd=backlog.parent.parent)

    assert result.returncode == 0
    assert "No slice is left" in result.stdout
    assert "##" not in result.stdout


def test_set_status_changes_only_the_named_slice(backlog):
    project = backlog.parent.parent

    result = run_script("set-status", "S02", "In progress", cwd=project)

    assert result.returncode == 0
    assert backlog.read_text() == BACKLOG.replace(
        "## S02: Edit a cell\n\nStatus: Todo",
        "## S02: Edit a cell\n\nStatus: In progress",
    )
    # A slice that is in progress is still the next one: `build` resumes it.
    assert "## S02" in run_script("next", cwd=project).stdout


def test_set_status_refuses_a_second_slice_in_progress(backlog):
    project = backlog.parent.parent
    run_script("set-status", "S02", "In progress", cwd=project)
    before = backlog.read_text()

    refused = run_script("set-status", "S03", "In progress", cwd=project)
    repeated = run_script("set-status", "S02", "In progress", cwd=project)

    assert refused.returncode == 1
    assert "S02" in refused.stderr
    assert repeated.returncode == 0
    assert backlog.read_text() == before


def test_finishing_a_slice_lets_the_next_one_start(backlog):
    project = backlog.parent.parent
    run_script("set-status", "S02", "in-progress", cwd=project)

    done = run_script("set-status", "S02", "done", cwd=project)
    started = run_script("set-status", "S03", "In progress", cwd=project)

    assert done.returncode == 0
    assert started.returncode == 0
    assert "## S03" in run_script("next", cwd=project).stdout


@pytest.mark.parametrize(
    ("arguments", "named"),
    [
        (("set-status", "S09", "Done"), "S09"),
        (("set-status", "S02", "Approved"), "Approved"),
    ],
)
def test_set_status_rejects_an_unknown_slice_or_status(backlog, arguments, named):
    result = run_script(*arguments, cwd=backlog.parent.parent)

    assert result.returncode != 0
    assert named in result.stderr
    assert backlog.read_text() == BACKLOG


@pytest.mark.parametrize("arguments", [("next",), ("set-status", "S01", "Done")])
def test_a_missing_or_malformed_backlog_is_an_error_that_names_the_cause(
    project, arguments
):
    missing = run_script(*arguments, cwd=project)
    (project / "docs" / "backlog.md").write_text(
        "# Backlog\n\nStatus: Approved\n\n## S01: First\n\nAcceptance criteria:\n- x\n"
    )
    malformed = run_script(*arguments, cwd=project)

    assert missing.returncode == 1
    assert "docs/backlog.md" in missing.stderr
    assert malformed.returncode == 1
    assert "S01" in malformed.stderr


EMPTY = "# Backlog\n\nStatus: Approved\n\nSlices, built in this order.\n"


def test_next_says_so_when_the_backlog_has_no_slices(backlog):
    backlog.write_text(EMPTY)

    result = run_script("next", cwd=backlog.parent.parent)

    assert result.returncode == 0
    assert "has no slices" in result.stdout
    assert "No slice is left" not in result.stdout


def test_archive_moves_every_slice_to_the_file_of_the_release(backlog):
    project = backlog.parent.parent
    backlog.write_text(BACKLOG.replace("Status: Todo", "Status: Done\nPR: #2"))
    slices = backlog.read_text().removeprefix(EMPTY + "\n")

    result = run_script("archive", "v0.1.0", cwd=project)

    assert result.returncode == 0
    assert "docs/backlog/v0.1.0.md" in result.stdout
    # The backlog keeps its title, status, and introduction, and nothing else.
    assert backlog.read_text() == EMPTY
    archive = (project / "docs" / "backlog" / "v0.1.0.md").read_text()
    assert archive.startswith("# Backlog of v0.1.0\n")
    assert archive.endswith(slices)
    assert "has no slices" in run_script("next", cwd=project).stdout


@pytest.mark.parametrize(
    ("text", "version", "named"),
    [
        (BACKLOG, "v0.1.0", "S02"),
        (EMPTY, "v0.1.0", "no slices"),
        (BACKLOG.replace("Todo", "Done"), "0.1", "vMAJOR.MINOR.PATCH"),
    ],
    ids=["a slice is not done", "nothing to archive", "not a version"],
)
def test_archive_refuses_and_changes_nothing(backlog, text, version, named):
    backlog.write_text(text)

    result = run_script("archive", version, cwd=backlog.parent.parent)

    assert result.returncode != 0
    assert named in result.stderr
    assert backlog.read_text() == text
    assert not (backlog.parent / "backlog").exists()


def test_archive_never_overwrites_an_earlier_release(backlog):
    project = backlog.parent.parent
    done = BACKLOG.replace("Status: Todo", "Status: Done")
    backlog.write_text(done)
    earlier = project / "docs" / "backlog" / "v0.1.0.md"
    earlier.parent.mkdir()
    earlier.write_text("# Backlog of v0.1.0\n")

    result = run_script("archive", "v0.1.0", cwd=project)

    assert result.returncode == 1
    assert "v0.1.0" in result.stderr
    assert backlog.read_text() == done
    assert earlier.read_text() == "# Backlog of v0.1.0\n"
