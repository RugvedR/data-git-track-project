# src/datagit/storage/repo.py
from pathlib import Path
from typing import Optional

def find_repo(start: Path = Path.cwd()) -> Optional[Path]:
    """
    Walk upward from start to find .datagit directory.
    Returns Path to repo root, or None if not found.
    """
    current = start.resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".datagit").exists():
            return parent / ".datagit"
    return None
