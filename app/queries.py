from functools import cache
from pathlib import Path


@cache
def load(path: Path) -> str:
    return path.read_text(encoding="utf-8")
