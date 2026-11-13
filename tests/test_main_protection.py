"""`main` protection: the agent commits on branches and never forces a push."""

import pytest
from conftest import git, run_hook

BLOCKED = 2


@pytest.fixture
def on_main(repository):
    """A project on `main` with one commit and a second branch, `feat/old`."""
    (repository / ".nightshift").touch()
    (repository / "src").mkdir()
    (repository / "src" / "app.txt").write_text("content\n")
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "-m", "chore: bootstrap")
    git(repository, "branch", "feat/old")
    return repository


@pytest.fixture
def on_branch(on_main):
    git(on_main, "switch", "--quiet", "-c", "feat/new")
    return on_main


def shell(project, command, cwd=None):
    return run_hook(
        "main_protection",
        {
            "hook_event_name": "PreToolUse",
            "cwd": str(cwd or project),
            "tool_name": "Bash",
            "tool_input": {"command": command},
        },
    )


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'feat: a change'",
        "git add --all && git commit -m x",
        "FOO=1 git -c user.name=agent commit --amend --no-edit",
        "cd src && git commit -m x",
        "git -C src commit -m x",
        # Checking out a file does not leave `main`.
        "git checkout src/app.txt && git commit -m x",
        "git switch -c feat/a && git switch main && git commit -m x",
    ],
)
def test_blocks_a_commit_on_main(on_main, command):
    result = shell(on_main, command)

    assert result.returncode == BLOCKED
    assert "branch" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "git status && git log --grep commit",
        "git commit-graph write",
        "echo 'git commit; git push --force'",
        "git switch -c feat/a && git commit -m x",
        "git checkout -b feat/a\ngit commit -m 'a; b'",
        "git switch feat/old && git commit -m x",
        "git fetch origin main && git pull",
        "git push origin v1.0.0",
        "git push --tags",
    ],
)
def test_allows_other_commands_on_main(on_main, command):
    assert shell(on_main, command).returncode == 0


@pytest.mark.parametrize(
    "command",
    [
        "git push",
        "git push -u origin HEAD",
        "git switch feat/old; git push origin main",
    ],
)
def test_blocks_a_push_of_main_from_main(on_main, command):
    result = shell(on_main, command)

    assert result.returncode == BLOCKED
    assert "pull request" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git push origin HEAD:main",
        "git push origin feat/new:refs/heads/main",
        "git push origin --delete main",
        "git push --all origin",
        "git switch main && git push",
    ],
)
def test_blocks_a_push_to_main_from_a_branch(on_branch, command):
    result = shell(on_branch, command)

    assert result.returncode == BLOCKED
    assert "pull request" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "git push --force",
        "git push -f origin feat/new",
        "git push -uf origin feat/new",
        "git push --force-with-lease origin feat/new",
        "git push origin +feat/new",
        "git push origin feat/new \\\n  --force",
        "result=$(git push --force 2>&1)",
    ],
)
def test_blocks_a_force_push(on_branch, command):
    result = shell(on_branch, command)

    assert result.returncode == BLOCKED
    assert "force" in result.stderr.lower()


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'fix: block git push --force to main'",
        "git commit -m \"$(cat <<'EOF'\nfeat: it's done; git push -f\nEOF\n)\"",
        "git commit -F - <<EOF\nfeat: it's done\nEOF",
        "git push",
        "git push -u origin feat/new",
        "git push -o ci.skip origin HEAD",
        "git push origin feat/new:feat/new",
        "git push origin main-menu",
    ],
)
def test_allows_commits_and_pushes_on_a_branch(on_branch, command):
    assert shell(on_branch, command).returncode == 0


def test_reads_the_branch_of_the_directory_the_session_is_in(on_main):
    result = shell(on_main, "git commit -m x", cwd=on_main / "src")

    assert result.returncode == BLOCKED


def test_allows_a_commit_on_a_detached_head(on_main):
    git(on_main, "switch", "--quiet", "--detach")

    assert shell(on_main, "git commit -m x").returncode == 0


def test_ignores_tools_other_than_the_shell(on_main):
    result = run_hook(
        "main_protection",
        {
            "hook_event_name": "PreToolUse",
            "cwd": str(on_main),
            "tool_name": "Write",
            "tool_input": {"file_path": "notes.md", "content": "git push --force"},
        },
    )

    assert result.returncode == 0


def test_does_nothing_without_the_marker(repository):
    for command in ("git commit -m x", "git push --force origin main"):
        assert shell(repository, command).returncode == 0
