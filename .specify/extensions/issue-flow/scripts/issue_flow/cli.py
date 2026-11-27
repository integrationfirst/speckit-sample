"""issue-flow CLI dispatcher. One JSON object on stdout per invocation."""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Callable

from issue_flow import config as config_mod  # noqa: E402
from issue_flow.config import ConfigError  # noqa: E402


# Workflows export "{{ inputs.dry_run | to_json }}" ("true"/"false"); shells use "1".
DRY_RUN_TRUE = ("1", "true", "yes")
DRY_RUN_FILE = "dry-run"   # .specify/issue-flow/<epic>/dry-run.json, written by init-mode/pull-issue
# Subcommands an agent step may run (the publish agent). Every other subcommand changes run
# state and needs ISSUE_FLOW_STEP=1, which only the workflows' shell steps set; the headless
# permissions also allow only these three.
AGENT_COMMANDS = frozenset({"request", "set-page", "pull-issue"})
STEP_ENV = "ISSUE_FLOW_STEP"


class Refusal(Exception):
    """Validation/refusal: exit 2."""


class Context:
    def __init__(self, root: Path, dry_run: bool = False, gh=None):
        self.root = Path(root)
        self.dry_run = dry_run
        self.env_dry_run = dry_run   # the env flag alone; dry_run may also come from state
        self._gh = gh
        self._config = None

    @property
    def gh(self):
        """GitHub adapter, built on first access from config (tests may inject one)."""
        if self._gh is None:
            from issue_flow.gh import GitHub
            self._gh = GitHub(self.config.repo, dry_run=self.dry_run)
        return self._gh

    @gh.setter
    def gh(self, value):
        self._gh = value

    def require_trigger_label(self, epic: int) -> None:
        """Refuse unless the Epic issue still carries the trigger label (removing the label
        stops the flow)."""
        label = self.config.trigger_label
        if label not in self.gh.issue(epic)["labels"]:
            raise Refusal(f"issue #{epic} no longer has the '{label}' label; flow stopped")

    @property
    def config(self):
        if self._config is None:
            self._config = config_mod.load(self.root)
        return self._config


class Waiting(Exception):
    """Result is valid but the stage is not approved yet: print it, exit 3."""

    def __init__(self, result: dict, message: str):
        super().__init__(message)
        self.result = result


# name -> (func, setup(parser) | None)
_REGISTRY: dict[str, tuple[Callable, Callable | None]] = {}


def register(name: str, func: Callable, setup: Callable | None = None) -> None:
    _REGISTRY[name] = (func, setup)


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")


class _Parser(argparse.ArgumentParser):
    """Help/usage/errors go to stderr so stdout carries only the JSON result."""

    def _print_message(self, message, file=None):
        if message:
            sys.stderr.write(message)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _Parser(prog="issue-flow")
    parser.add_argument("--root", default=None, help="project root (default: cwd)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_, setup) in sorted(_REGISTRY.items()):
        sp = sub.add_parser(name)
        if setup:
            setup(sp)
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 2
        if code != 0:
            _emit({"error": "invalid arguments"})
            return 2
        _emit({"help": True})
        return 0
    try:
        if args.command not in AGENT_COMMANDS and os.environ.get(STEP_ENV, "") != "1":
            raise Refusal(f"'{args.command}' runs only from a workflow shell step "
                          f"({STEP_ENV}=1); agent steps may run only "
                          f"{', '.join(sorted(AGENT_COMMANDS))}")
        ctx = Context(Path(args.root) if args.root else Path.cwd(),
                      dry_run=os.environ.get("ISSUE_FLOW_DRY_RUN", "").strip().lower() in DRY_RUN_TRUE)
        # Sticky per epic: a run started dry (pull-issue writes dry-run.json, a CLI-only file)
        # stays dry for every later command, including those run by agent steps that do not
        # inherit the workflow's env.
        # The opposite also holds: a dry run on a real-run state dir is refused, because
        # agent steps (which do not get the env) would then make real GitHub writes.
        epic = getattr(args, "epic", None)
        if epic is not None:
            from issue_flow.state import StateDir
            mode = StateDir(ctx.root, epic).read(DRY_RUN_FILE)
            if ctx.dry_run and "dry_run" in mode and not mode["dry_run"]:
                raise Refusal(f"epic #{epic} state is from a real run; remove "
                              f".specify/issue-flow/{epic}/ to start a dry run")
            if not ctx.dry_run:
                ctx.dry_run = bool(mode.get("dry_run"))
        func = _REGISTRY[args.command][0]
        _emit(func(args, ctx))
        return 0
    except Waiting as e:
        _emit(e.result)
        sys.stderr.write(str(e) + "\n")
        return 3
    except (Refusal, ConfigError) as e:
        _emit({"error": str(e)})
        return 2
    except Exception as e:  # noqa: BLE001
        traceback.print_exc(file=sys.stderr)
        _emit({"error": f"{type(e).__name__}: {e}"})
        return 1
