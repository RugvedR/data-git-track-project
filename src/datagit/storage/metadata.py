# src/datagit/storage/metadata.py
import json
from pathlib import Path

def load_metadata(repo_path: Path) -> dict:
    metadata_path = repo_path / "metadata.json"
    if metadata_path.exists():
        return json.loads(metadata_path.read_text())
    return {"HEAD": None, "branch": "main", "commits": []}

def save_metadata(repo_path: Path, metadata: dict) -> None:
    metadata_path = repo_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
