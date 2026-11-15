"""The project's status line and `nightshift.py usage`, which reads what it saved."""

import json
import subprocess
from pathlib import Path

from conftest import ROOT, run_script

STATUS_LINE = {
    "session_id": "abc",
    "context_window": {"used_percentage": 42.6, "context_window_size": 200000},
    "rate_limits": {
        "five_hour": {"used_percentage": 27, "resets_at": 1763200000},
        "seven_day": {"used_percentage": 61.2, "resets_at": 1763700000},
    },
}


def show_status_line(project: Path, payload: dict) -> None:
    """Run the template's status line command as Claude Code does."""
    settings = json.loads((ROOT / "templates" / "settings.json").read_text())
    subprocess.run(
        settings["statusLine"]["command"],
        shell=True,
        cwd=project,
        input=json.dumps(payload),
        check=True,
        text=True,
    )


def test_usage_prints_what_the_status_line_last_saved(repository):
    show_status_line(repository, {"context_window": {"used_percentage": 3}})
    show_status_line(repository, STATUS_LINE)

    result = run_script("usage", cwd=repository)

    assert result.returncode == 0
    assert result.stdout == "Context 43% · 5h 27% · week 61%\n"


def test_usage_marks_what_claude_code_did_not_pass(repository):
    # Plan limits are absent, for example, when the session uses an API key.
    show_status_line(repository, {"context_window": {"used_percentage": 8}})

    result = run_script("usage", cwd=repository)

    assert result.stdout == "Context 8% · 5h ? · week ?\n"


def test_usage_says_how_to_record_it_when_nothing_was_saved(repository):
    result = run_script("usage", cwd=repository)

    assert result.returncode == 0
    assert "Usage unknown" in result.stdout
    assert "templates/settings.json" in result.stdout
