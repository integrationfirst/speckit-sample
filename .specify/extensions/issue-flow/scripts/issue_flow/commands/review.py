"""pull-issue, request, check-approval, record-feature."""
from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from issue_flow import cli
from issue_flow.approvals import content_hash, evaluate, next_request_id, parse_command
from issue_flow.state import StateDir

MAX_BODY = 60000
STAGES = ["spec", "plan", "tasks", "qa", "pr"]
REVIEW_HEADING = "### Review requested"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_branch(root: Path) -> str:
    return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root,
                          capture_output=True, text=True, check=True).stdout.strip()


def _is_flow_comment(body: str) -> bool:
    """Review requests posted by the flow and /approve|/reject commands: not issue content."""
    text = (body or "").strip()
    if not text:
        return False
    first = text.splitlines()[0].strip()
    return first.startswith(REVIEW_HEADING) or parse_command(first) is not None


def _head(root: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as e:
        raise cli.Refusal("cannot read the current commit (git rev-parse HEAD failed)") from e


def _digest(ctx, stage: str, paths: list[Path]) -> str:
    """Content hash of the artifacts; for qa also of the commit under test, so a QA approval
    never survives a code change."""
    h = content_hash(paths, base=ctx.root)
    if stage == "qa":
        h = hashlib.sha256(f"{h}\0head={_head(ctx.root)}".encode()).hexdigest()
    return h


def _artifact_paths(ctx, artifacts: list[str]) -> list[Path]:
    root = ctx.root.resolve()
    paths = []
    for a in artifacts:
        if Path(a).is_absolute():
            raise cli.Refusal(f"artifact must be a path relative to the project: {a}")
        p = (ctx.root / a).resolve()
        if not p.is_relative_to(root):
            raise cli.Refusal(f"artifact is outside the project: {a}")
        if not p.is_file():
            raise cli.Refusal(f"artifact not found: {a}")
        paths.append(ctx.root / a)
    return paths


def _check_mode(state: StateDir, epic: int, ctx) -> dict:
    """The recorded run mode; refuse when the step env asks for the other mode."""
    mode = state.read(cli.DRY_RUN_FILE)
    if mode.get("dry_run") and not ctx.env_dry_run:
        raise cli.Refusal(f"epic #{epic} state is from a dry run; remove "
                          f".specify/issue-flow/{epic}/ to start a real run")
    if "dry_run" in mode and not mode["dry_run"] and ctx.env_dry_run:
        raise cli.Refusal(f"epic #{epic} state is from a real run; remove "
                          f".specify/issue-flow/{epic}/ to start a dry run")
    return mode


# -- init-mode
def init_mode(args, ctx) -> dict:
    """Record the run mode from the step env (ISSUE_FLOW_DRY_RUN) unless already recorded, so
    agent steps, which do not get the env, follow it. Workflows run this before any agent step
    that may call the CLI."""
    state = StateDir(ctx.root, args.epic)
    mode = _check_mode(state, args.epic, ctx)
    if "dry_run" not in mode:
        mode = {"dry_run": bool(ctx.env_dry_run)}
        state.write(cli.DRY_RUN_FILE, mode)
    return {"epic": args.epic, "dry_run": bool(mode["dry_run"])}


# -- pull-issue
def pull_issue(args, ctx) -> dict:
    state = StateDir(ctx.root, args.epic)
    mode = _check_mode(state, args.epic, ctx)
    issue = ctx.gh.issue(args.epic)
    label = ctx.config.trigger_label
    if label not in issue["labels"]:
        raise cli.Refusal(f"issue #{args.epic} does not have the '{label}' label")
    lines = [f"# {issue['title']}", "", f"Source: {issue['url']}", "", issue["body"], "", "## Comments", ""]
    for c in ctx.gh.comments(args.epic):
        if _is_flow_comment(c["body"]):
            continue
        lines += [f"**@{c['author']}** ({c['createdAt']}):", c["body"], ""]
    rel = Path(".specify/issue-flow") / str(args.epic) / "issue.md"
    path = ctx.root / rel
    state.ensure()
    path.write_text("\n".join(lines))
    if "dry_run" not in mode:
        state.write(cli.DRY_RUN_FILE, {"dry_run": bool(ctx.dry_run)})
    return {"epic": args.epic, "title": issue["title"], "path": rel.as_posix()}


# -- request
def _fence(text: str) -> str:
    import re
    n = max([len(m) for m in re.findall(r"`+", text)] + [2]) + 1
    return "`" * n


def _logins(ctx, stage: str) -> list[str]:
    out: list[str] = []
    for r in ctx.config.stages[stage].roles:
        for lg in ctx.config.approvers.get(r, []):
            if lg not in out:
                out.append(lg)
    return out


def _body(ctx, stage, rid, summary, page_url, artifacts) -> str:
    head = [f"{REVIEW_HEADING}: {stage} — {rid}", ""]
    if summary:
        head += [summary, ""]
    tail = []
    logins = _logins(ctx, stage)
    if logins:
        tail += ["Approvers: " + " ".join(f"@{lg}" for lg in logins), ""]
    tail += [f"/approve {rid}", f"/reject {rid} <reason>"]
    tail_s = "\n".join(tail)
    if page_url:
        mid = [f"Document: {page_url}", ""]
        return "\n".join(head + mid) + "\n" + tail_s
    fixed = len("\n".join(head)) + len(tail_s) + 200
    budget = MAX_BODY - fixed
    mid: list[str] = []
    truncated = False
    for rel, text in artifacts:
        if budget <= 0:
            truncated = True
            break
        if len(text) > budget:
            text, truncated = text[:budget], True
        budget -= len(text) + len(rel) + 20
        f = _fence(text)
        mid += [f"{rel}:", f"{f}markdown", text, f, ""]
        if truncated:
            mid += [f"(truncated — full file: {rel})", ""]
            break
    return "\n".join(head + mid) + "\n" + tail_s


def request(args, ctx) -> dict:
    stage = args.stage
    if stage not in ctx.config.stages:
        raise cli.Refusal(f"unknown stage '{stage}'")
    paths = _artifact_paths(ctx, args.artifact)
    ctx.require_trigger_label(args.epic)
    digest = _digest(ctx, stage, paths)
    state = StateDir(ctx.root, args.epic)
    reqs = state.read("requests")
    history = reqs.get(stage, [])
    if history and history[-1]["hash"] == digest:
        last = history[-1]
        status = evaluate(last, ctx.gh.comments(last["target"]), ctx.config.stages[stage],
                          ctx.config.approvers, digest)["status"]
        if status == "rejected":
            raise cli.Refusal(f"artifact unchanged since rejected {last['id']}; "
                              "revise it before re-requesting")
        if last["comment_id"] != 0 or ctx.dry_run:
            return {**last, "reused": True}
        # a dry-run record never posted a comment: fall through and post for real
    rid = next_request_id(reqs, stage)
    body = _body(ctx, stage, rid, getattr(args, "summary", None), getattr(args, "page_url", None),
                 [(a, p.read_text(errors="replace")) for a, p in zip(args.artifact, paths)])
    posted_at = now()
    comment_id = ctx.gh.comment(args.target, body)
    rec = {"id": rid, "stage": stage, "target": args.target, "hash": digest,
           "posted_at": posted_at, "artifacts": list(args.artifact),
           "comment_id": comment_id, "page_url": getattr(args, "page_url", None) or ""}
    reqs.setdefault(stage, []).append(rec)
    state.write("requests", reqs)
    return {**rec, "reused": False}


# -- check-approval
def check_approval(args, ctx) -> dict:
    stage = args.stage
    if stage not in ctx.config.stages:
        raise cli.Refusal(f"unknown stage '{stage}'")
    if ctx.config.stages[stage].via == "github_review":
        raise cli.Refusal(f"stage '{stage}' is approved via github_review, not comments; "
                          "use pr-status")
    state = StateDir(ctx.root, args.epic)
    history = state.read("requests").get(stage, [])
    if not history:
        raise cli.Refusal(f"no approval request recorded for stage '{stage}'")
    req = history[-1]
    target = getattr(args, "target", None)
    if target is not None and req["target"] != target:
        # The latest request is for another issue (e.g. the previous Story's QA): never let
        # its approval satisfy this wait.
        result = {"status": "pending", "request_id": None, "target": target, "approved_by": {},
                  "waiting_for": list(ctx.config.stages[stage].roles), "reason": "", "feedback": ""}
        state.write(stage, result)
        if getattr(args, "wait", False):
            raise cli.Waiting(result, f"waiting for a {stage} request: no {stage} request for "
                                      f"#{target} yet (latest {req['id']} is for #{req['target']})")
        return result
    paths = [ctx.root / a for a in req["artifacts"]]
    missing = [a for a, p in zip(req["artifacts"], paths) if not p.is_file()]
    current = "missing:" + ",".join(missing) if missing else _digest(ctx, stage, paths)
    result = evaluate(req, ctx.gh.comments(req["target"]), ctx.config.stages[stage],
                      ctx.config.approvers, current)
    state.write(stage, result)
    if getattr(args, "wait", False) and result["status"] == "pending":
        roles = result["waiting_for"]
        logins = []
        for r in roles:
            logins += [f"@{lg}" for lg in ctx.config.approvers.get(r, []) if f"@{lg}" not in logins]
        raise cli.Waiting(result, f"waiting for {', '.join(roles)} ({', '.join(logins)}) "
                                  f"on #{req['target']} — comment /approve {req['id']}")
    return result


# -- assert-published
def assert_published(args, ctx) -> dict:
    """Exit 2 unless the latest request for the stage is for `target`, matches the current
    artifacts and is not rejected (run after an agent publish so a failed publish stops)."""
    stage = args.stage
    if stage not in ctx.config.stages:
        raise cli.Refusal(f"unknown stage '{stage}'")
    history = StateDir(ctx.root, args.epic).read("requests").get(stage, [])
    if not history:
        raise cli.Refusal(f"not published: no {stage} request recorded")
    req = history[-1]
    if req["target"] != args.target:
        raise cli.Refusal(f"not published: latest {stage} request {req['id']} is for "
                          f"#{req['target']}, not #{args.target}")
    if not ctx.dry_run and not req.get("comment_id"):
        raise cli.Refusal(f"not published: {req['id']} was recorded by a dry run and never posted")
    try:
        paths = _artifact_paths(ctx, req["artifacts"])
    except cli.Refusal as e:
        raise cli.Refusal(f"not published: {e}") from e
    current = _digest(ctx, stage, paths)
    if current != req["hash"]:
        raise cli.Refusal(f"not published: the {stage} artifact changed after {req['id']} "
                          "was requested; publish again")
    status = evaluate(req, ctx.gh.comments(req["target"]), ctx.config.stages[stage],
                      ctx.config.approvers, current)["status"]
    if status == "rejected":
        raise cli.Refusal(f"not published: {req['id']} is rejected and was not superseded; "
                          "revise the artifact and publish again")
    return {"published": True, "stage": stage, "request_id": req["id"], "target": req["target"],
            "status": status}


# -- set-page
PAGE_KEYS = ["spec", "plan", "tasks", "tasks-breakdown"]


def set_page(args, ctx) -> dict:
    """Record a Confluence page id in state.json `pages` (the publish agent may not write the
    state dir itself)."""
    import re
    if not re.fullmatch(r"[0-9]{1,30}", args.page_id):
        raise cli.Refusal(f"page id must be numeric: {args.page_id!r}")
    state = StateDir(ctx.root, args.epic)
    st = state.read("state")
    pages = st.get("pages") if isinstance(st.get("pages"), dict) else {}
    pages[args.key] = args.page_id
    st["pages"] = pages
    state.write("state", st)
    return {"epic": args.epic, "pages": pages}


# -- record-feature
def record_feature(args, ctx) -> dict:
    branch = _git_branch(ctx.root)
    fdir = f"specs/{branch}"
    if not (ctx.root / fdir).is_dir():
        raise cli.Refusal(f"feature directory not found: {fdir}")
    state = StateDir(ctx.root, args.epic)
    st = state.read("state")
    st.update(feature_branch=branch, feature_dir=fdir)
    state.write("state", st)
    return {"feature_branch": branch, "feature_dir": fdir}


def _epic(sp):
    sp.add_argument("--epic", type=int, required=True)


def _setup_request(sp):
    _epic(sp)
    sp.add_argument("--stage", required=True, choices=STAGES)
    sp.add_argument("--target", type=int, required=True)
    sp.add_argument("--artifact", action="append", required=True)
    sp.add_argument("--page-url", dest="page_url", default=None)
    sp.add_argument("--summary", default=None)


def _setup_assert(sp):
    _epic(sp)
    sp.add_argument("--stage", required=True, choices=STAGES)
    sp.add_argument("--target", type=int, required=True)


def _setup_check(sp):
    _epic(sp)
    sp.add_argument("--stage", required=True, choices=STAGES)
    sp.add_argument("--target", type=int, default=None,
                    help="issue the request must be for (required by the workflow for qa)")
    sp.add_argument("--wait", action="store_true")


def _setup_page(sp):
    _epic(sp)
    sp.add_argument("--key", required=True, choices=PAGE_KEYS)
    sp.add_argument("--page-id", dest="page_id", required=True)


cli.register("init-mode", init_mode, _epic)
cli.register("set-page", set_page, _setup_page)
cli.register("pull-issue", pull_issue, _epic)
cli.register("request", request, _setup_request)
cli.register("check-approval", check_approval, _setup_check)
cli.register("record-feature", record_feature, _epic)
cli.register("assert-published", assert_published, _setup_assert)
