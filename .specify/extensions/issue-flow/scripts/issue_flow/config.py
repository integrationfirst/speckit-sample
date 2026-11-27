"""Config loader for issue-flow."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_REL = Path(".specify/extensions/issue-flow/issue-flow-config.yml")
_BRANCH_RE = re.compile(r"[A-Za-z0-9._][A-Za-z0-9._/-]*")


class ConfigError(Exception):
    pass


@dataclass
class StageCfg:
    roles: list[str]
    require: str = "all"
    via: str = "comment"


@dataclass
class Suite:
    name: str
    type: str
    command: str
    required: bool = True
    timeout_seconds: int = 1800


@dataclass
class TestsCfg:
    max_fix_rounds: int = 5
    suites: list[Suite] = field(default_factory=list)


@dataclass
class GitCfg:
    default_branch: str = "main"


@dataclass
class Config:
    repo: str
    trigger_label: str
    progress_labels: dict[str, str]
    confluence: dict
    approvers: dict[str, list[str]]
    stages: dict[str, StageCfg]
    tests: TestsCfg
    git: GitCfg


def _map(d, key):
    v = d.get(key) or {}
    if not isinstance(v, dict):
        raise ConfigError(f"'{key}' must be a mapping")
    return v


def _str_list(v, where: str, allow_empty: bool = True) -> list[str]:
    """A list of non-empty strings. A scalar is an error (never split into characters)."""
    if not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
        raise ConfigError(f"{where} must be a list of non-empty strings")
    if not allow_empty and not v:
        raise ConfigError(f"{where} must not be empty")
    return list(v)


def _read_yaml(text: str, where: str) -> dict:
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"invalid YAML in {where}: {e}")
    if not isinstance(raw, dict):
        raise ConfigError(f"config root must be a mapping ({where})")
    return raw


_GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}
NET_TIMEOUT = 60


def _run_git(root: Path, args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess | None:
    """git via argv; None when git is missing or a network call times out. Never prompts."""
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                              env={**os.environ, **_GIT_ENV}, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _git_show(root: Path, ref: str) -> str | None:
    """Contents of the config file at `ref` (path relative to `root`), or None."""
    r = _run_git(root, ["show", f"{ref}:./{CONFIG_REL.as_posix()}"])
    return r.stdout if r is not None and r.returncode == 0 else None


def _repo_of_url(url: str) -> str | None:
    """owner/name of a github.com remote URL (https or ssh), lower-cased; None otherwise."""
    m = re.fullmatch(r"(?:https://(?:[^@/]+@)?github\.com/|ssh://git@github\.com/|git@github\.com:)"
                     r"([^/]+/[^/]+?)(?:\.git)?/?", url.strip())
    return m.group(1).lower() if m else None


def _origin_url(root: Path) -> str | None:
    r = _run_git(root, ["remote", "get-url", "origin"])
    return r.stdout.strip() if r is not None and r.returncode == 0 else None


def _check_origin(url: str, repo: str) -> None:
    """origin must be the configured GitHub repo (a local path is accepted only for tests and
    mirrors that are not on github.com)."""
    got = _repo_of_url(url)
    if "github.com" in url and got != repo.lower():
        raise ConfigError(f"origin ({url}) is not github.repo '{repo}'; approvers are read only "
                          "from the configured repository")


def _origin_default_branch(root: Path) -> str | None:
    """The default branch of `origin`, asked from the remote itself; when it cannot be reached,
    the local origin/HEAD. None when neither is known."""
    r = _run_git(root, ["ls-remote", "--symref", "origin", "HEAD"], timeout=NET_TIMEOUT)
    if r is not None and r.returncode == 0:
        m = re.search(r"^ref: refs/heads/(\S+)\tHEAD$", r.stdout, re.M)
        if m and _BRANCH_RE.fullmatch(m.group(1)):
            return m.group(1)
    r = _run_git(root, ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if r is not None and r.returncode == 0:
        b = r.stdout.strip().removeprefix("origin/")
        if _BRANCH_RE.fullmatch(b):
            sys.stderr.write(f"issue-flow: origin unreachable; using local origin/{b}\n")
            return b
    return None


def _fetch(root: Path, branch: str) -> None:
    """Refresh origin/<branch> so approver changes pushed since the last fetch are seen; offline,
    keep the existing ref (GitHub writes and approval checks need the network anyway)."""
    r = _run_git(root, ["fetch", "--quiet", "--no-tags", "origin",
                        f"+refs/heads/{branch}:refs/remotes/origin/{branch}"], timeout=NET_TIMEOUT)
    if r is None or r.returncode != 0:
        err = (r.stderr.strip() if r is not None else "timed out")
        sys.stderr.write(f"issue-flow: cannot fetch origin/{branch} ({err}); using the local ref\n")


def _committed(root: Path, wt_default_branch: str, repo: str) -> tuple[dict, str]:
    """The config committed on origin's default branch, freshly fetched. Only a project
    without an `origin` remote falls back to the local branch named by the working tree
    (`git.default_branch`)."""
    url = _origin_url(root)
    if url is not None:
        _check_origin(url, repo)
        remote_default = _origin_default_branch(root)
        if remote_default is None:
            raise ConfigError("cannot determine the default branch of 'origin' (unreachable and "
                              "no local origin/HEAD); approvers are read from it")
        _fetch(root, remote_default)
        ref = f"origin/{remote_default}"
    else:
        ref = wt_default_branch
    text = _git_show(root, ref)
    if text is None:
        raise ConfigError(
            f"issue-flow config is not committed on {ref}: commit and push "
            f"{CONFIG_REL.as_posix()} to the default branch before a run "
            "(approvers, stages and git settings are read only from there)")
    return _read_yaml(text, f"{ref}:{CONFIG_REL.as_posix()}"), ref


def _git_cfg(raw: dict) -> GitCfg:
    g = _map(raw, "git")
    default_branch = g.get("default_branch", "main")
    if not isinstance(default_branch, str) or not _BRANCH_RE.fullmatch(default_branch):
        raise ConfigError("git.default_branch must be a branch name")
    stacked = g.get("stacked", True)
    if stacked is not True:
        raise ConfigError("git.stacked: unstacked mode was removed in issue-flow 0.1.1 (Story "
                          "PRs always stack); delete the setting")
    return GitCfg(default_branch=default_branch)


def _approvers(raw: dict) -> dict[str, list[str]]:
    return {str(k): _str_list(v, f"approvers.{k}") for k, v in _map(raw, "approvers").items()}


def _stages(raw: dict, approvers: dict[str, list[str]]) -> dict[str, StageCfg]:
    stages: dict[str, StageCfg] = {}
    for name, s in _map(raw, "stages").items():
        if not isinstance(s, dict):
            raise ConfigError(f"stages.{name} must be a mapping")
        roles = _str_list(s.get("roles"), f"stages.{name}.roles", allow_empty=False)
        for r in roles:
            if r not in approvers:
                raise ConfigError(f"stage '{name}' references unknown role '{r}'")
        require = s.get("require", "all")
        via = s.get("via", "comment")
        if require not in ("all", "any"):
            raise ConfigError(f"stage '{name}': require must be 'all' or 'any'")
        if via not in ("comment", "github_review"):
            raise ConfigError(f"stage '{name}': via must be 'comment' or 'github_review'")
        stages[name] = StageCfg(roles=roles, require=require, via=via)
    return stages


def _suites(t: dict) -> list[Suite]:
    raw = t.get("suites") or []
    if not isinstance(raw, list):
        raise ConfigError("tests.suites must be a list")
    suites = []
    for i, s in enumerate(raw):
        where = f"tests.suites[{i}]"
        if not isinstance(s, dict):
            raise ConfigError(f"{where} must be a mapping")
        for k in ("name", "type", "command"):
            if k not in s:
                raise ConfigError(f"{where} missing '{k}'")
            if not isinstance(s[k], str) or not s[k].strip():
                raise ConfigError(f"{where}.{k} must be a non-empty string")
        required = s.get("required", True)
        timeout = s.get("timeout_seconds", 1800)
        if not isinstance(required, bool):
            raise ConfigError(f"{where}.required must be true or false")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise ConfigError(f"{where}.timeout_seconds must be a positive integer")
        suites.append(Suite(name=s["name"], type=s["type"], command=s["command"],
                            required=required, timeout_seconds=timeout))
    return suites


def load(root: Path) -> Config:
    """Working-tree config, except `approvers`, `stages` and `git`: those are read from the
    config committed on the remote's default branch (fetched first), so an agent editing the
    working tree cannot change who may approve or where PRs go."""
    root = Path(root)
    path = root / CONFIG_REL
    if not path.is_file():
        raise ConfigError(f"config not found: {path}")
    raw = _read_yaml(path.read_text(), str(path))

    gh = _map(raw, "github")
    repo = gh.get("repo")
    if not repo or not isinstance(repo, str):
        raise ConfigError("github.repo is required")

    wt_git = _git_cfg(raw)   # validated, but only used to locate the config without a remote
    committed, _ = _committed(root, wt_git.default_branch, repo)
    git = _git_cfg(committed)
    approvers = _approvers(committed)
    stages = _stages(committed, approvers)

    t = _map(raw, "tests")
    rounds = t.get("max_fix_rounds", 5)
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 1:
        raise ConfigError("tests.max_fix_rounds must be a positive integer")
    tests = TestsCfg(max_fix_rounds=rounds, suites=_suites(t))

    return Config(
        repo=repo,
        trigger_label=gh.get("trigger_label", "coding-agent"),
        progress_labels=dict(_map(gh, "progress_labels")),
        confluence=dict(_map(raw, "confluence")),
        approvers=approvers, stages=stages, tests=tests, git=git)
