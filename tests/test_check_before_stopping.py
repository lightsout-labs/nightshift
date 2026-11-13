"""Stop hook: the agent cannot stop a slice while `make check` fails."""

import json

import pytest
from conftest import git, run_hook

BLOCKED = 2

BACKLOG = "# Backlog\n\nStatus: Approved\n\n## S01: First\n\nStatus: {status}\n"


class Building:
    """A project with a slice in progress. Its `make check` records every run
    and fails while the file `broken` exists."""

    def __init__(self, root, log):
        self.root = root
        self.log = log
        (root / "Makefile").write_text(
            "check:\n"
            f'\t@echo run >> "{log}"\n'
            '\t@if [ -f broken ]; then echo "lint: boom in app.py"; exit 1; fi\n'
        )
        (root / "app.py").write_text("x = 1\n")
        self.set_slice("In progress")
        git(root, "add", "--all")
        git(root, "commit", "--quiet", "-m", "start")

    def set_slice(self, status):
        (self.root / "docs" / "backlog.md").write_text(BACKLOG.format(status=status))

    def break_check(self):
        (self.root / "broken").touch()

    def fix_check(self):
        (self.root / "broken").unlink()

    def stop(self):
        return run_hook(
            "check_before_stopping",
            {"hook_event_name": "Stop", "cwd": str(self.root)},
        )

    def runs(self):
        return len(self.log.read_text().splitlines()) if self.log.exists() else 0


@pytest.fixture
def building(repository, project, tmp_path_factory):
    return Building(project, tmp_path_factory.mktemp("runs") / "log")


def test_blocks_the_stop_and_passes_the_output_when_the_check_fails(building):
    building.break_check()

    result = building.stop()

    assert result.returncode == BLOCKED
    assert "make check" in result.stderr
    assert "lint: boom in app.py" in result.stderr


def test_allows_the_stop_when_the_check_passes(building):
    result = building.stop()

    assert result.returncode == 0
    assert result.stdout == ""
    assert building.runs() == 1


def test_third_failure_in_a_row_sends_the_agent_to_the_human(building):
    building.break_check()
    assert building.stop().returncode == BLOCKED
    assert building.stop().returncode == BLOCKED

    third = building.stop()

    # Not a block: the agent is told to ask, with the output to report.
    assert third.returncode == 0
    feedback = json.loads(third.stdout)["hookSpecificOutput"]
    assert feedback["hookEventName"] == "Stop"
    assert "human" in feedback["additionalContext"]
    assert "lint: boom in app.py" in feedback["additionalContext"]

    # The stop that asks the human goes through without another run.
    asking = building.stop()
    assert asking.returncode == 0
    assert asking.stdout == ""
    assert building.runs() == 3

    # After the human answers, the agent has three attempts again.
    assert building.stop().returncode == BLOCKED


def test_a_passing_run_resets_the_count(building):
    building.break_check()
    assert building.stop().returncode == BLOCKED
    assert building.stop().returncode == BLOCKED
    building.fix_check()
    assert building.stop().returncode == 0

    building.break_check()

    assert building.stop().returncode == BLOCKED
    assert building.stop().returncode == BLOCKED


@pytest.mark.parametrize("status", ["Todo", "Done"])
def test_does_not_run_the_check_when_no_slice_is_in_progress(building, status):
    building.set_slice(status)
    building.break_check()

    result = building.stop()

    assert result.returncode == 0
    assert building.runs() == 0


def test_does_not_run_the_check_without_a_backlog(building):
    (building.root / "docs" / "backlog.md").unlink()
    building.break_check()

    assert building.stop().returncode == 0
    assert building.runs() == 0


def test_does_not_run_the_check_again_until_the_working_tree_changes(building):
    assert building.stop().returncode == 0
    assert building.stop().returncode == 0
    assert building.runs() == 1

    (building.root / "app.py").write_text("x = 2\n")

    assert building.stop().returncode == 0
    assert building.runs() == 2


def test_keeps_its_state_in_the_git_directory_out_of_git_status(building):
    before = git(building.root, "status", "--porcelain")
    staged = git(building.root, "diff", "--cached", "--name-only")

    building.stop()
    (building.root / "app.py").write_text("x = 2\n")
    building.break_check()
    building.stop()
    building.fix_check()
    git(building.root, "checkout", "--", "app.py")

    assert (building.root / ".git" / "nightshift").is_dir()
    assert git(building.root, "status", "--porcelain") == before
    assert git(building.root, "diff", "--cached", "--name-only") == staged


def test_does_nothing_without_the_marker(building):
    (building.root / ".nightshift").unlink()
    building.break_check()

    assert building.stop().returncode == 0
    assert building.runs() == 0
