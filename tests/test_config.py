"""`nightshift.py config`: the project's settings, read from `.nightshift`."""

import pytest
from conftest import ROOT, run_script

DEFAULTS = "language: English\nci: yes\nstop-after-slice: yes\n"


def test_an_empty_marker_gives_the_defaults(project):
    result = run_script("config", cwd=project)

    assert result.returncode == 0
    assert result.stdout == DEFAULTS


def test_the_template_holds_the_defaults(project):
    (project / ".nightshift").write_text(
        (ROOT / "templates" / "nightshift").read_text()
    )

    assert run_script("config", cwd=project).stdout == DEFAULTS


def test_settings_in_the_marker_replace_the_defaults(project):
    (project / ".nightshift").write_text("stop-after-slice: no\nlanguage:  简体中文 \n")

    result = run_script("config", cwd=project)

    assert result.returncode == 0
    assert result.stdout == "language: 简体中文\nci: yes\nstop-after-slice: no\n"


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("colour: blue\n", "line 1: unknown setting 'colour'"),
        ("ci: yes\nci maybe\n", "line 2: unknown setting 'ci maybe'"),
        ("ci: sometimes\n", "line 1: ci must be yes or no"),
        ("language:\n", "line 1: language must not be empty"),
    ],
)
def test_a_malformed_setting_is_refused_with_its_line(project, text, reason):
    (project / ".nightshift").write_text(text)

    result = run_script("config", cwd=project)

    assert result.returncode == 1
    assert result.stderr == f".nightshift: {reason}\n"


def test_a_marker_that_is_not_utf8_is_refused(project):
    (project / ".nightshift").write_bytes(b"language: \xff\n")

    result = run_script("config", cwd=project)

    assert result.returncode == 1
    assert result.stderr == ".nightshift: is not UTF-8 text\n"


def test_outside_a_project_it_says_where_to_run_it(tmp_path):
    result = run_script("config", cwd=tmp_path)

    assert result.returncode == 1
    assert "run this from the project root" in result.stderr
