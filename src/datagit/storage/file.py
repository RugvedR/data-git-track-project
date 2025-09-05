# src/datagit/storage/file.py
import hashlib
import shutil
import json
from pathlib import Path

def hash_file(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

def save_object(file_path: Path, file_hash: str, repo_path: Path) -> Path:
    """
    Save a file into the .datagit/objects/ store using its hash.
    """
    objects_dir = repo_path / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)

    dest = objects_dir / file_hash
    if not dest.exists():
        shutil.copy(file_path, dest)

    return dest

def load_index(repo_path: Path) -> dict:
    """
    Load the staging index.json file.
    """
    index_path = repo_path / "index.json"
    if index_path.exists():
        return json.loads(index_path.read_text())
    return {}

def save_index(repo_path: Path, index: dict):
    """
    Save the staging index.json file.
    """
    index_path = repo_path / "index.json"
    index_path.write_text(json.dumps(index, indent=2))

def build_index_entry(file_path: Path, file_hash: str) -> dict:
    """
    Create index entry with hash + basic metadata.
    """
    stat = file_path.stat()
    return {
        "hash": file_hash,
        "size": stat.st_size,
        "mtime": stat.st_mtime
    }

def list_working_files(repo_root: Path) -> set[str]:
    """
    Return all file paths under repo_root (relative to repo_root),
    excluding the .datagit directory.
    """
    return {
        str(p.relative_to(repo_root))
        for p in repo_root.rglob("*")
        if p.is_file() and ".datagit" not in str(p)
    }
