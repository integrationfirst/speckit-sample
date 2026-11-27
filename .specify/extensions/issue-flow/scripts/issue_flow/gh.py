"""GitHub adapter over the `gh` CLI. All calls use argv lists (never a shell);
untrusted text is passed as a single field value or via stdin."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Callable
from urllib.parse import quote


class GhError(RuntimeError):
    """gh exited non-zero."""


def run_gh(args: list[str], input: str | None = None) -> str:
    try:
        return subprocess.run(["gh", *args], input=input, capture_output=True,
                              text=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        raise GhError(f"gh {' '.join(args[:3])} failed (exit {e.returncode}): "
                      f"{(e.stderr or '').strip()}") from e


def _parse_pages(out: str) -> list:
    """Parse `--paginate [--slurp]` output: array of pages, or concatenated arrays."""
    dec, i, items = json.JSONDecoder(), 0, []
    out = out.strip()
    while i < len(out):
        val, i = dec.raw_decode(out, i)
        while i < len(out) and out[i].isspace():
            i += 1
        items.extend(val) if isinstance(val, list) else items.append(val)
    flat: list = []
    for it in items:  # slurp wraps each page (a list) in an outer list
        flat.extend(it) if isinstance(it, list) else flat.append(it)
    return flat


def _login(u) -> str:
    return (u or {}).get("login", "") or ""


def _trunc(s: str, n: int = 200) -> str:
    return s if len(s) <= n else s[:n] + "...[truncated]"


def _trunc_arg(a: str) -> str:
    """Truncate the value of `key=value` fields (the key is kept intact)."""
    k, eq, v = a.partition("=")
    return f"{k}={_trunc(v)}" if eq and (k.isidentifier() or k.endswith("[]")) else _trunc(a)


class GitHub:
    def __init__(self, repo: str, runner: Callable[..., str] = run_gh, dry_run: bool = False):
        self.repo, self.runner, self.dry_run = repo, runner, dry_run
        self.owner, _, self.name = repo.partition("/")

    # -- helpers
    def _read_pages(self, path: str) -> list:
        return _parse_pages(self.runner(["api", "--paginate", "--slurp", path]))

    def _graphql(self, query: str, **fields) -> dict:
        argv = ["api", "graphql", "-f", f"query={query}"]
        for k, v in fields.items():
            argv += ["-F" if isinstance(v, int) else "-f", f"{k}={v}"]
        return json.loads(self.runner(argv))

    def _write(self, argv: list[str], input: str | None = None, fake=None):
        """Run a write, or log it and return `fake` in dry-run."""
        if self.dry_run:
            shown = " ".join(_trunc_arg(a) for a in argv)
            if input is not None:
                shown += f" <stdin:{_trunc(input)}>"
            print(f"DRY-RUN gh {shown}", file=sys.stderr)
            return fake
        return self.runner(argv) if input is None else self.runner(argv, input)

    # -- reads
    def issue(self, n: int) -> dict:
        d = json.loads(self.runner(["api", f"repos/{self.repo}/issues/{n}"]))
        return {"number": d["number"], "title": d.get("title") or "", "body": d.get("body") or "",
                "labels": [lb["name"] for lb in d.get("labels", [])],
                "state": d.get("state", ""), "url": d.get("html_url", "")}

    def comments(self, n: int) -> list[dict]:
        return [{"id": c["id"], "author": _login(c.get("user")), "body": c.get("body") or "",
                 "createdAt": c.get("created_at", ""), "updatedAt": c.get("updated_at", "")}
                for c in self._read_pages(f"repos/{self.repo}/issues/{n}/comments")]

    def pr_reviews(self, pr: int) -> list[dict]:
        return [{"author": _login(r.get("user")), "state": r.get("state", ""),
                 "body": r.get("body") or "", "submittedAt": r.get("submitted_at") or "",
                 "commit_id": r.get("commit_id") or ""}
                for r in self._read_pages(f"repos/{self.repo}/pulls/{pr}/reviews")]

    def pr_review_comments(self, pr: int) -> list[dict]:
        return [{"author": _login(c.get("user")), "body": c.get("body") or "",
                 "path": c.get("path", ""), "line": c.get("line"),
                 "createdAt": c.get("created_at", "")}
                for c in self._read_pages(f"repos/{self.repo}/pulls/{pr}/comments")]

    def sub_issues(self, n: int) -> list[int]:
        q = ("query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name)"
             "{issue(number:$number){subIssues(first:100){nodes{number}}}}}")
        d = self._graphql(q, owner=self.owner, name=self.name, number=n)
        return [x["number"] for x in d["data"]["repository"]["issue"]["subIssues"]["nodes"]]

    def _node_id(self, n: int) -> str:
        q = ("query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name)"
             "{issue(number:$number){id}}}")
        d = self._graphql(q, owner=self.owner, name=self.name, number=n)
        return d["data"]["repository"]["issue"]["id"]

    # -- writes
    def comment(self, n: int, body: str) -> int:
        out = self._write(["api", "-X", "POST", f"repos/{self.repo}/issues/{n}/comments",
                           "-f", f"body={body}"], fake=None)
        return 0 if out is None else json.loads(out)["id"]

    def create_issue(self, title: str, body: str, labels: list[str]) -> int:
        argv = ["issue", "create", "--repo", self.repo, "--title", title, "--body-file", "-"]
        for lb in labels:
            argv += ["--label", lb]
        out = self._write(argv, input=body)
        return 0 if out is None else int(re.search(r"/(\d+)\s*$", out).group(1))

    def add_sub_issue(self, parent: int, child: int) -> None:
        if self.dry_run:
            self._write(["api", "graphql", "-f",
                         f"query=mutation addSubIssue(parent={parent}, child={child})"])
            return
        pid, cid = self._node_id(parent), self._node_id(child)
        m = ("mutation($issueId:ID!,$subIssueId:ID!){addSubIssue(input:{issueId:$issueId,"
             "subIssueId:$subIssueId}){issue{id}}}")
        self._graphql(m, issueId=pid, subIssueId=cid)

    def add_labels(self, n: int, labels: list[str]) -> None:
        argv = ["api", "-X", "POST", f"repos/{self.repo}/issues/{n}/labels"]
        for lb in labels:
            argv += ["-f", f"labels[]={lb}"]
        self._write(argv)

    def remove_labels(self, n: int, labels: list[str]) -> None:
        for lb in labels:
            self._write(["api", "-X", "DELETE",
                         f"repos/{self.repo}/issues/{n}/labels/{quote(lb, safe='')}"])

    def edit_issue_body(self, n: int, body: str) -> None:
        self._write(["api", "-X", "PATCH", f"repos/{self.repo}/issues/{n}", "-f", f"body={body}"])

    def pr_create(self, head: str, base: str, title: str, body: str) -> dict:
        out = self._write(["pr", "create", "--repo", self.repo, "--head", head, "--base", base,
                           "--title", title, "--body-file", "-"], input=body)
        if out is None:
            return {"number": 0, "url": "dry-run"}
        url = out.strip().splitlines()[-1]
        return {"number": int(url.rstrip("/").rsplit("/", 1)[-1]), "url": url}

    def pr_comment(self, pr: int, body: str) -> None:
        self.comment(pr, body)
