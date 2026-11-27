"""start-story, open-pr, pr-status."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone

from issue_flow import cli, prs
from issue_flow.gh import GhError
from issue_flow.state import StateDir

git = prs.git


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sname(story: int) -> str:
    return f"stories/{story}/state"


def _find(state: StateDir, story: int):
    m = state.read("issue-mapping")
    if not m:
        raise cli.Refusal("no issue-mapping.json; run create-stories first")
    for i, s in enumerate(m["stories"]):
        if s["number"] == story:
            return m, i, s
    raise cli.Refusal(f"unknown story #{story}")


def _set_status(state: StateDir, m: dict, s: dict, status: str) -> None:
    s["status"] = status
    state.write("issue-mapping", m)


def _commit_feature_docs(root, fb: str, feature_dir: str, epic: int) -> None:
    """On the feature branch, commit uncommitted changes under feature_dir (no-op if clean)."""
    current = git(["rev-parse", "--abbrev-ref", "HEAD"], root).strip()
    if current != fb:
        raise cli.Refusal(f"the first story must start from the feature branch '{fb}' "
                          f"(currently on '{current}'); check out '{fb}' and resume")
    if not feature_dir or not git(["status", "--porcelain", "--", feature_dir], root).strip():
        return
    git(["add", "--", feature_dir], root)
    git(["commit", "-q", "-m", f"docs(#{epic}): spec, plan and tasks", "--", feature_dir], root)


def start_story(args, ctx) -> dict:
    state = StateDir(ctx.root, args.epic)
    st0 = state.read("state")
    fb = st0.get("feature_branch")
    if not fb:
        raise cli.Refusal("no feature_branch recorded; run record-feature first")
    m, i, story = _find(state, args.story)
    ctx.require_trigger_label(args.epic)
    cfg = ctx.config
    branches = {s["number"]: state.read(_sname(s["number"])).get("branch") for s in m["stories"][:i]}
    picked = prs.pick_base(m["stories"], i, branches, fb, cfg.git.default_branch)
    if not picked:
        raise cli.Refusal("previous story has no branch yet; start it first")
    branch_point, base = picked
    branch = prs.branch_name(args.story, story["title"])
    try:
        exists = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
                                cwd=ctx.root, capture_output=True).returncode == 0
        if not exists and i == 0:
            # the spec documents travel with Story 1's PR
            _commit_feature_docs(ctx.root, fb, st0.get("feature_dir", ""), args.epic)
        git(["checkout", branch] if exists else ["checkout", "-b", branch, branch_point], ctx.root)
    except subprocess.CalledProcessError as e:
        raise cli.Refusal(f"git failed: {(e.stderr or '').strip()}") from e
    st = state.read(_sname(args.story))
    st.update(branch=branch, base=base, branch_point=branch_point)
    state.write(_sname(args.story), st)
    label = cfg.progress_labels.get("in_progress")
    if label:
        ctx.gh.add_labels(args.story, [label])
    _set_status(state, m, story, "in_progress")
    return {"branch": branch, "base": base, "branch_point": branch_point}


def open_pr(args, ctx) -> dict:
    state = StateDir(ctx.root, args.epic)
    m, _, story = _find(state, args.story)
    st = state.read(_sname(args.story))
    branch, base = st.get("branch"), st.get("base")
    if not branch or not base:
        raise cli.Refusal(f"story #{args.story} has no branch; run start-story first")
    rep = ctx.root / ".specify/issue-flow" / str(args.epic) / "stories" / str(args.story) / "test-report.md"
    report = rep.read_text(errors="replace") if rep.is_file() else ""
    ctx.require_trigger_label(args.epic)
    # Clear the reviewed head before pushing: if rev-parse fails after the push, the old
    # SHA must not stay valid (pr-status fails closed on an empty head_sha).
    st.update(push_started_at=now(), head_sha="")
    state.write(_sname(args.story), st)
    prj = state.read(f"stories/{args.story}/pr")
    prj["head_sha"] = ""
    state.write(f"stories/{args.story}/pr", prj)
    if ctx.dry_run:
        print(f"DRY-RUN git push -u origin {branch}", file=sys.stderr)
    else:
        try:
            git(["push", "-u", "origin", branch], ctx.root)
        except subprocess.CalledProcessError as e:
            raise cli.Refusal(f"git push failed: {(e.stderr or '').strip()}") from e
    # Persist push facts before any gh write so a later failure cannot leave stale approvals valid.
    pushed_at = now()
    head_sha = "" if ctx.dry_run else git(["rev-parse", "HEAD"], ctx.root).strip()
    st.update(last_push_at=pushed_at, head_sha=head_sha)
    state.write(_sname(args.story), st)
    prj.update(branch=branch, base=base, last_push_at=pushed_at, head_sha=head_sha)
    state.write(f"stories/{args.story}/pr", prj)
    if st.get("pr"):
        pr, url, created = st["pr"], st.get("pr_url", ""), False
        ctx.gh.pr_comment(pr, f"### New push — test report\n\n{report or '_No test report available._'}")
    else:
        res = ctx.gh.pr_create(head=branch, base=base, title=f"{story['title']} (#{args.story})",
                               body=prs.render_pr_body(story, args.epic, report))
        pr, url, created = res["number"], res["url"], True
    st.update(pr=pr, pr_url=url)
    state.write(_sname(args.story), st)
    prj.update(pr=pr, url=url)
    state.write(f"stories/{args.story}/pr", prj)
    labels = ctx.config.progress_labels
    if labels.get("in_progress"):
        try:
            ctx.gh.remove_labels(args.story, [labels["in_progress"]])
        except GhError as e:
            if "404" not in str(e) and "Not Found" not in str(e):
                raise
    if labels.get("in_review"):
        ctx.gh.add_labels(args.story, [labels["in_review"]])
    _set_status(state, m, story, "in_review")
    return {"pr": pr, "url": url, "created": created}


def pr_status(args, ctx) -> dict:
    state = StateDir(ctx.root, args.epic)
    st = state.read(_sname(args.story))
    pr = st.get("pr")
    if not pr:
        raise cli.Refusal(f"story #{args.story} has no pull request; run open-pr first")
    cfg = ctx.config
    stage = cfg.stages["pr"]
    role_logins = {r: list(cfg.approvers.get(r, [])) for r in stage.roles}
    logins = [lg for lgs in role_logins.values() for lg in lgs]
    since = max(st.get("last_push_at", ""), st.get("push_started_at", ""))
    head_sha = st.get("head_sha", "")
    if not st.get("last_push_at") or not head_sha:
        res = {"status": "pending", "waiting_for": list(role_logins)}  # fail closed
    else:
        res = prs.evaluate_reviews(ctx.gh.pr_reviews(pr), ctx.gh.pr_review_comments(pr),
                                   role_logins, stage.require, since, head_sha)
    res.update(pr=pr, url=st.get("pr_url", ""))
    prj = state.read(f"stories/{args.story}/pr")
    prj.update(res)
    state.write(f"stories/{args.story}/pr", prj)
    if getattr(args, "wait", False) and res["status"] == "pending":
        raise cli.Waiting(res, f"waiting for PR review from {', '.join(logins)} on {res['url']}")
    return res


def _setup(sp):
    sp.add_argument("--epic", type=int, required=True)
    sp.add_argument("--story", type=int, required=True)


def _setup_status(sp):
    _setup(sp)
    sp.add_argument("--wait", action="store_true")


cli.register("start-story", start_story, _setup)
cli.register("open-pr", open_pr, _setup)
cli.register("pr-status", pr_status, _setup_status)
