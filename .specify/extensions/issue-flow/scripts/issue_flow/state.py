"""Per-epic state directory: .specify/issue-flow/<epic>/<name>.json"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class StateDir:
    def __init__(self, root: Path, epic: int):
        self.base = Path(root) / ".specify" / "issue-flow"
        self.path = self.base / str(epic)

    def ensure(self) -> Path:
        """Create the epic dir, and `.specify/issue-flow/.gitignore` (`*`) so run state is
        never committed (the agent steps commit with `git add`)."""
        self.path.mkdir(parents=True, exist_ok=True)
        gi = self.base / ".gitignore"
        if not gi.is_file():
            gi.write_text("*\n")
        return self.path

    def _file(self, name: str) -> Path:
        return self.path / f"{name}.json"

    def read(self, name: str) -> dict:
        f = self._file(name)
        if not f.is_file():
            return {}
        return json.loads(f.read_text())

    def write(self, name: str, data: dict) -> None:
        f = self._file(name)
        self.ensure()
        f.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=f.parent, prefix=f.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump(data, fh, indent=2, sort_keys=True)
                fh.write("\n")
            os.replace(tmp, f)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
