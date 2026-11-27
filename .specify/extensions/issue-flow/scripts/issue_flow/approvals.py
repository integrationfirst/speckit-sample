"""Pure approval logic: request ids, content hashing, command parsing, evaluation."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from issue_flow.config import StageCfg

_CMD = re.compile(r"^/(approve|reject)[ \t]+(IF-[a-z]+-r\d+)(?:[ \t]+(.*))?$", re.IGNORECASE)


def next_request_id(requests: dict, stage: str) -> str:
    return f"IF-{stage}-r{len(requests.get(stage, [])) + 1}"


def content_hash(paths: list[Path], base: Path | None = None) -> str:
    """sha256 over sorted (relative path, bytes). `base` makes paths relative."""
    items = []
    for p in paths:
        p = Path(p)
        items.append((p.relative_to(base).as_posix() if base else p.as_posix(), p.read_bytes()))
    h = hashlib.sha256()
    for rel, data in sorted(items):
        h.update(rel.encode() + b"\0" + str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()


def parse_command(body: str) -> tuple[str, str, str] | None:
    """Only the whole first line of a comment is a command."""
    first = (body or "").strip().splitlines()[0].strip() if (body or "").strip() else ""
    m = _CMD.match(first)
    if not m:
        return None
    return m.group(1).lower(), m.group(2), (m.group(3) or "").strip()


def evaluate(request: dict, comments: list[dict], stage: StageCfg,
             approvers: dict[str, list[str]], current_hash: str) -> dict:
    rid, posted = request["id"], request["posted_at"]
    result = {"status": "pending", "request_id": rid, "approved_by": {},
              "waiting_for": list(stage.roles), "reason": "", "feedback": ""}
    if current_hash != request["hash"]:
        result["status"] = "stale"
        return result

    # latest relevant command per login (by updatedAt; later list position breaks ties)
    latest: dict[str, tuple[str, int, str, str]] = {}
    for idx, c in enumerate(comments):
        if not (c.get("createdAt", "") > posted or c.get("updatedAt", "") > posted):
            continue
        cmd = parse_command(c.get("body", ""))
        if not cmd or cmd[1] != rid:
            continue
        login = c.get("author", "")
        key = (c.get("updatedAt", "") or c.get("createdAt", ""), idx)
        if login.lower() not in latest or key >= latest[login.lower()][:2]:
            latest[login.lower()] = (key[0], key[1], login, cmd[0] + "\0" + cmd[2])

    approved: dict[str, str] = {}
    rejects: list[tuple[str, str]] = []
    for _, _, login, packed in sorted(latest.values()):
        action, reason = packed.split("\0", 1)
        roles = [r for r in stage.roles
                 if login.lower() in {a.lower() for a in approvers.get(r, [])}]
        if not roles:
            continue
        if action == "reject":
            rejects.append((login, reason))
        else:
            for r in roles:
                approved[r] = login

    if rejects:
        result["status"] = "rejected"
        result["reason"] = rejects[0][1]
        result["feedback"] = "\n".join(f"@{lg}: {rs}" for lg, rs in rejects)
        return result
    result["approved_by"] = {r: approved[r] for r in stage.roles if r in approved}
    done = bool(approved) if stage.require == "any" else all(r in approved for r in stage.roles)
    if done and stage.roles:
        result["status"] = "approved"
        result["waiting_for"] = []
    else:
        result["waiting_for"] = [r for r in stage.roles if r not in approved]
    return result
