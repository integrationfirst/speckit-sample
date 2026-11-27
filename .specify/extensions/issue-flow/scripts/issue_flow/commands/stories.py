"""breakdown, create-stories, next-story, set-story-status."""
from __future__ import annotations

from pathlib import Path

from issue_flow import cli
from issue_flow.approvals import content_hash
from issue_flow.state import StateDir
from issue_flow.stories import StoryError, parse_tasks, plan_stories, render_breakdown, story_body

STATUSES = ["todo", "in_progress", "in_review", "done"]


def _tasks_path(args, ctx, state: StateDir) -> Path:
    if getattr(args, "tasks", None):
        return ctx.root / args.tasks
    fdir = state.read("state").get("feature_dir")
    if not fdir:
        raise cli.Refusal("no feature_dir recorded; run record-feature or pass --tasks")
    return ctx.root / fdir / "tasks.md"


def _plan(path: Path):
    if not path.is_file():
        raise cli.Refusal(f"tasks file not found: {path}")
    try:
        return plan_stories(parse_tasks(path.read_text()))
    except StoryError as e:
        raise cli.Refusal(str(e)) from e


def _summary(plans) -> list[dict]:
    return [{"title": p.title, "task_ids": [t.id for t in p.tasks]} for p in plans]


def breakdown(args, ctx) -> dict:
    state = StateDir(ctx.root, args.epic)
    plans = _plan(_tasks_path(args, ctx, state))
    state.ensure()
    (state.path / "breakdown.md").write_text(render_breakdown(plans))
    return {"stories": _summary(plans)}


def _require_approved(ctx, state: StateDir, tasks_path: Path) -> None:
    approval = state.read("tasks")
    if approval.get("status") != "approved":
        raise cli.Refusal("tasks stage is not approved")
    hist = state.read("requests").get("tasks", [])
    bd = state.path / "breakdown.md"
    if not hist or not bd.is_file() or not tasks_path.is_file():
        raise cli.Refusal("tasks stage is not approved for the current breakdown "
                          "(no request or missing tasks.md/breakdown.md)")
    if approval.get("request_id") != hist[-1]["id"]:
        raise cli.Refusal(f"the tasks approval is for {approval.get('request_id')}, not the "
                          f"latest request {hist[-1]['id']}; wait for its approval")
    if hist[-1]["hash"] != content_hash([tasks_path, bd], base=ctx.root):
        raise cli.Refusal("tasks.md/breakdown.md changed since approval; re-request approval")


def create_stories(args, ctx) -> dict:
    epic = args.epic
    state = StateDir(ctx.root, epic)
    tpath = _tasks_path(args, ctx, state)
    _require_approved(ctx, state, tpath)
    ctx.require_trigger_label(epic)
    plans = _plan(tpath)
    if (state.path / "breakdown.md").read_text() != render_breakdown(plans):
        raise cli.Refusal("breakdown.md does not match tasks.md; "
                          "re-run breakdown and get it re-approved")
    mapping = state.read("issue-mapping") or {"epic": epic, "stories": []}
    stories = mapping["stories"]
    label = ctx.config.trigger_label
    result: list[dict] = []
    for i, plan in enumerate(plans):
        ids = [t.id for t in plan.tasks]
        have = stories[i] if i < len(stories) else None
        if have and have.get("number") and have["title"] == plan.title:
            rec = have
        else:
            n = ctx.gh.create_issue(plan.title, story_body(epic, i, plan), [label])
            if ctx.dry_run or not n:
                ctx.gh.add_sub_issue(epic, n)
                result.append({"number": None, "title": plan.title, "task_ids": ids,
                               "status": "todo", "dry_run": True})
                continue
            rec = {"number": n, "title": plan.title, "task_ids": ids,
                   "status": "todo", "linked": False}
            del stories[i:]          # drop any stale mapping at/after this index
            stories.append(rec)
            state.write("issue-mapping", {"epic": epic, "stories": stories})  # before linking
        if not rec.get("linked", True):
            ctx.gh.add_sub_issue(epic, rec["number"])
            rec["linked"] = True
            state.write("issue-mapping", {"epic": epic, "stories": stories})
        result.append(rec)
    return {"epic": epic, "stories": result}


def _mapping(state: StateDir) -> dict:
    m = state.read("issue-mapping")
    if not m:
        raise cli.Refusal("no issue-mapping.json; run create-stories first")
    return m


def next_story(args, ctx) -> dict:
    m = _mapping(StateDir(ctx.root, args.epic))
    for i, s in enumerate(m["stories"]):
        if s["status"] != "done":
            return {"story": s["number"], "index": i, "title": s["title"], "task_ids": s["task_ids"]}
    return {"story": None, "index": None, "title": None, "task_ids": []}


def set_story_status(args, ctx) -> dict:
    if args.status not in STATUSES:
        raise cli.Refusal(f"invalid status '{args.status}' (one of {', '.join(STATUSES)})")
    state = StateDir(ctx.root, args.epic)
    m = _mapping(state)
    for s in m["stories"]:
        if s["number"] == args.story:
            s["status"] = args.status
            state.write("issue-mapping", m)
            return {"story": args.story, "status": args.status}
    raise cli.Refusal(f"unknown story #{args.story}")


def _epic(sp):
    sp.add_argument("--epic", type=int, required=True)


def _setup_breakdown(sp):
    _epic(sp)
    sp.add_argument("--tasks", default=None)


def _setup_status(sp):
    _epic(sp)
    sp.add_argument("--story", type=int, required=True)
    sp.add_argument("--status", required=True)


cli.register("breakdown", breakdown, _setup_breakdown)
cli.register("create-stories", create_stories, _epic)
cli.register("next-story", next_story, _epic)
cli.register("set-story-status", set_story_status, _setup_status)
