#!/usr/bin/env python3
"""UserPromptSubmit hook: the human approves by typing `approve`.

When the whole prompt is `approve` or `approved`, every gated document that
is `Draft` becomes `Approved`, and the list is printed for the agent. This
event fires only for text the human submits, and the hook edits the files
itself, so the agent cannot trigger it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import nightshift  # noqa: E402

WORDS = {"approve", "approved"}


def main() -> int:
    event = json.load(sys.stdin)
    project = nightshift.find_project(event.get("cwd") or ".")
    if project is None or event.get("prompt", "").strip().lower() not in WORDS:
        return 0
    approved = nightshift.approve_drafts(project)
    if approved:
        print("The human approved these documents. Their status is now Approved:")
        print("\n".join(f"- {path}" for path in approved))
        print("Commit the change and continue as the stage's skill says.")
    else:
        print("No document is waiting for approval. Tell the human.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
