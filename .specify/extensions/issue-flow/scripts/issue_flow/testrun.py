"""Pure test-runner logic: run suites, render the report."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

TAIL_LINES = 80


@dataclass
class SuiteResult:
    name: str
    type: str
    required: bool
    ok: bool
    duration: float
    output: str  # combined stdout+stderr, or the timeout message
    result: str  # "pass" | "fail" | "timed out after Ns"


def run_suite(suite, root: Path) -> SuiteResult:
    """Run one configured suite command (config-sourced only) in root, capturing all output."""
    start = time.monotonic()
    proc = subprocess.Popen(suite.command, shell=True, cwd=root, encoding="utf-8", errors="replace",
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=suite.timeout_seconds)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        msg = f"timed out after {suite.timeout_seconds}s"
        return SuiteResult(suite.name, suite.type, suite.required, False,
                           time.monotonic() - start, msg, msg)
    ok = proc.returncode == 0
    return SuiteResult(suite.name, suite.type, suite.required, ok,
                       time.monotonic() - start, out or "", "pass" if ok else "fail")


def _fence(text: str) -> str:
    import re
    n = max([len(m) for m in re.findall(r"`+", text)] + [2]) + 1
    return "`" * n


def render_report(story: int, rnd: int, max_rounds: int, results: list[SuiteResult],
                  head: str = "", run_at: str = "") -> str:
    lines = [f"# Test report — story #{story} — round {rnd}/{max_rounds}", "",
             f"Commit: `{head or 'unknown'}`  ", f"Run at: {run_at or 'unknown'}", "",
             "| Suite | Type | Required | Result | Duration |",
             "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r.name} | {r.type} | {'yes' if r.required else 'no'} | "
                     f"{r.result} | {r.duration:.1f}s |")
    for r in results:
        if r.ok:
            continue
        tail = "\n".join(r.output.splitlines()[-TAIL_LINES:])
        f = _fence(tail)
        lines += ["", f"### {r.name}", "", f, tail, f]
    return "\n".join(lines) + "\n"
