"""Pure logic for story branches and pull requests."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

DECISIVE = ("APPROVED", "CHANGES_REQUESTED", "DISMISSED")


def slugify(title: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:max_len].strip("-")


def branch_name(story: int, title: str) -> str:
    return f"{story}-{slugify(title)}"


def git(args: list[str], cwd: Path) -> str:
    """Run git via argv (never a shell); raises CalledProcessError on failure."""
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          check=True).stdout


def pick_base(stories: list[dict], index: int, branches: dict[int, str],
              feature_branch: str, default_branch: str) -> tuple[str, str] | None:
    """(branch point, PR base) for story `index`; None when the previous story has no branch.
    Story 1 branches from the (unpushed) feature branch, so it carries the spec documents, but
    its PR targets the default branch; Story N stacks on Story N-1."""
    if index == 0:
        return feature_branch, default_branch
    prev = branches.get(stories[index - 1]["number"])
    return (prev, prev) if prev else None


def render_pr_body(story: dict, epic: int, report: str) -> str:
    lines = [f"## {story['title']}", "", "### Tasks"]
    lines += [f"- [ ] {t}" for t in story.get("task_ids", [])]
    lines += ["", f"Closes #{story['number']}", f"Part of #{epic}", "",
              "### Latest test report", "", report or "_No test report available._"]
    return "\n".join(lines)


def evaluate_reviews(reviews: list[dict], comments: list[dict], role_logins: dict[str, list[str]],
                     require: str, since: str, head_sha: str) -> dict:
    """Only reviews by role members, on `head_sha`, submitted after `since` count (logins compared
    case-insensitively); latest decisive review per login. `require` is 'all' or 'any' roles."""
    allowed = {lg.lower() for lgs in role_logins.values() for lg in lgs}
    latest: dict[str, dict] = {}
    for r in sorted((r for r in reviews if r["author"].lower() in allowed
                     and r["state"] in DECISIVE and r["submittedAt"] > since
                     and head_sha and r.get("commit_id", "") == head_sha),
                    key=lambda r: r["submittedAt"]):
        latest[r["author"].lower()] = r
    changes = [r for r in latest.values() if r["state"] == "CHANGES_REQUESTED"]
    if changes:
        fb = [f"@{r['author']}: {r['body']}" for r in changes if r["body"].strip()]
        fb += [f"@{c['author']} {c['path']}:{c['line']}: {c['body']}" for c in comments
               if c["author"].lower() in allowed and c["createdAt"] > since]
        return {"status": "changes_requested", "feedback": "\n".join(fb)}
    approved = {role for role, lgs in role_logins.items()
                if any(latest.get(lg.lower(), {}).get("state") == "APPROVED" for lg in lgs)}
    done = bool(approved) if require == "any" else bool(role_logins) and approved == set(role_logins)
    if done:
        return {"status": "approved"}
    return {"status": "pending", "waiting_for": [r for r in role_logins if r not in approved]}
