"""Plugin structure: what Claude Code needs in order to load the plugin."""

import json
import re

import pytest
from conftest import ROOT

SKILL_LINE_BUDGET = 80
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
AGENTS = sorted((ROOT / "agents").glob("*.md"))


def load(relative):
    return json.loads((ROOT / relative).read_text())


def frontmatter(skill):
    match = re.match(r"---\n(.*?)\n---\n", skill.read_text(), re.DOTALL)
    assert match, f"{skill} has no frontmatter"
    return dict(line.split(": ", 1) for line in match.group(1).splitlines())


def test_plugin_manifest_names_the_plugin():
    manifest = load(".claude-plugin/plugin.json")

    assert manifest["name"] == "nightshift"
    assert manifest["description"]


def test_marketplace_offers_this_repository_as_the_plugin():
    marketplace = load(".claude-plugin/marketplace.json")

    assert marketplace["name"]
    assert marketplace["owner"]["name"]
    (entry,) = marketplace["plugins"]
    assert entry["name"] == load(".claude-plugin/plugin.json")["name"]
    assert entry["source"] == "./"


@pytest.mark.parametrize("stage", ["spec", "design", "slice", "build"])
def test_the_stage_has_a_skill(stage):
    assert ROOT / "skills" / stage / "SKILL.md" in SKILLS


@pytest.mark.parametrize("skill", SKILLS, ids=lambda skill: skill.parent.name)
def test_skill_has_frontmatter_and_stays_within_the_line_budget(skill):
    fields = frontmatter(skill)

    assert fields["name"] == skill.parent.name
    assert fields["description"]
    assert len(skill.read_text().splitlines()) <= SKILL_LINE_BUDGET


SKILL_FILES = sorted((ROOT / "skills").glob("*/*.md"))


@pytest.mark.parametrize(
    "path", SKILL_FILES, ids=lambda path: f"{path.parent.name}/{path.name}"
)
def test_every_plugin_file_a_skill_names_exists(path):
    named = re.findall(
        r"(?:\$\{CLAUDE_PLUGIN_ROOT\}|PLUGIN)/([\w./-]+)", path.read_text()
    )

    for relative in named:
        assert (ROOT / relative).is_file(), f"{path} names missing {relative}"


def test_the_slice_reviewer_is_the_only_agent_and_is_read_only():
    (agent,) = AGENTS
    fields = frontmatter(agent)

    assert fields["name"] == agent.stem == "slice-reviewer"
    assert fields["description"]
    assert fields["tools"] == "Read"
    assert "disallowedTools" not in fields
    assert len(agent.read_text().splitlines()) <= SKILL_LINE_BUDGET


def test_only_the_build_skill_launches_the_reviewer():
    launching = {
        path.parent.name for path in SKILL_FILES if "slice-reviewer" in path.read_text()
    }

    assert launching == {"build"}
    build = (ROOT / "skills" / "build" / "SKILL.md").read_text()
    assert "`nightshift:slice-reviewer`" in build


def test_the_pull_request_template_has_a_place_for_the_review_result():
    template = (ROOT / "templates" / "pull-request.md").read_text()

    assert "\n## Review\n" in template


def test_every_registered_hook_command_points_at_a_hook_file():
    events = load("hooks/hooks.json")["hooks"]
    commands = [
        hook["command"]
        for registrations in events.values()
        for registration in registrations
        for hook in registration["hooks"]
    ]

    assert commands
    for command in commands:
        (relative,) = re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", command)
        assert (ROOT / relative).is_file(), f"hooks.json names missing {relative}"
