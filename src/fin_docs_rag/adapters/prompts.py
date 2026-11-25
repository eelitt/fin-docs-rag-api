import re
from pathlib import Path

from fin_docs_rag.ports import DependencyFailure

_ID = re.compile(r"[a-z0-9_]+")


class FilePrompts:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load(self, prompt_id: str) -> str:
        if _ID.fullmatch(prompt_id) is None:
            raise DependencyFailure("prompt")
        path = self._root / f"{prompt_id}.md"
        if not path.is_file():
            raise DependencyFailure("prompt")
        return path.read_text(encoding="utf-8")
