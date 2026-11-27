"""Pure tasks.md parsing and Story planning (no I/O, no gh)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from issue_flow.cli import Refusal

PHASE_RE = re.compile(r"^## Phase \d+: (.+)$")
TASK_RE = re.compile(r"^- \[( |x|X)\] (T\d{3,})\b(.*)$")
_KINDS = [("Setup", "setup"), ("Foundational", "foundational"),
          ("User Story", "user_story"), ("Polish", "polish")]


class StoryError(Refusal):
    """Malformed tasks.md (a Refusal: exit 2)."""


@dataclass
class Task:
    id: str
    text: str
    done: bool

    def line(self) -> str:
        return f"- [{'x' if self.done else ' '}] {self.id} {self.text}".rstrip()


@dataclass
class Phase:
    title: str
    kind: str
    tasks: list[Task] = field(default_factory=list)


@dataclass
class StoryPlan:
    title: str
    tasks: list[Task]


def _kind(title: str) -> str:
    for prefix, kind in _KINDS:
        if title.startswith(prefix):
            return kind
    return "other"


def parse_tasks(md: str) -> list[Phase]:
    phases: list[Phase] = []
    for n, line in enumerate(md.splitlines(), 1):
        line = line.rstrip()
        m = PHASE_RE.match(line)
        if m:
            title = m.group(1).strip()
            phases.append(Phase(title, _kind(title)))
            continue
        t = TASK_RE.match(line)
        if t:
            if not phases:
                raise StoryError(f"task {t.group(2)} (line {n}) is outside any '## Phase N:' section")
            phases[-1].tasks.append(Task(t.group(2), t.group(3).strip(), t.group(1) != " "))
    return phases


def plan_stories(phases: list[Phase]) -> list[StoryPlan]:
    if not any(p.kind == "user_story" for p in phases):
        raise StoryError('no "User Story" phase found in tasks.md')
    plans: list[StoryPlan] = []
    pending: list[Task] = []   # setup/foundational/other before the first story
    tail: list[Task] = []      # polish anywhere
    for p in phases:
        if p.kind == "user_story":
            plans.append(StoryPlan(p.title, pending + list(p.tasks)))
            pending = []
        elif p.kind == "polish":
            tail += p.tasks
        elif plans:
            plans[-1].tasks += p.tasks
        else:
            pending += p.tasks
    plans[-1].tasks += tail
    return plans


def render_breakdown(plans: list[StoryPlan]) -> str:
    out = ["# Story breakdown", ""]
    for i, s in enumerate(plans, 1):
        out += [f"## Story {i}: {s.title}", ""] + [t.line() for t in s.tasks] + [""]
    return "\n".join(out)


def story_body(epic: int, index: int, plan: StoryPlan) -> str:
    return "\n".join([f"Part of #{epic}", ""] + [t.line() for t in plan.tasks]
                     + ["", f"<!-- issue-flow:story epic={epic} index={index} -->"])
