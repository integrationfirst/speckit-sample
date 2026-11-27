"""Command modules. Later tasks append their module name to MODULES; each
module calls issue_flow.cli.register(...) at import time."""
MODULES: list[str] = ["review", "stories", "testrun", "prs"]
