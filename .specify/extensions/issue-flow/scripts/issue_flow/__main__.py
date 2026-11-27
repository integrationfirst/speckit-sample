"""Entry point: python3 -m issue_flow (PYTHONPATH=<ext>/scripts).

Running as a package module keeps a single `issue_flow.cli` module, so command
modules importing it share one registry and one Refusal class.
"""
import importlib
import os
import sys

from issue_flow import cli
from issue_flow.commands import MODULES

# ISSUE_FLOW_COMMAND_MODULES: extra comma-separated modules (used by tests/plugins).
_extra = [m for m in os.environ.get("ISSUE_FLOW_COMMAND_MODULES", "").split(",") if m]
for _m in [*(f"issue_flow.commands.{m}" if "." not in m else m for m in MODULES), *_extra]:
    importlib.import_module(_m)

sys.exit(cli.main())
