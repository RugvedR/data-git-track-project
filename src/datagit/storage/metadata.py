import json
from pathlib import Path
from typing import Dict, Any

# --- Metadata (metadata.json) ---

def load_metadata(repo_path: Path) -> Dict[str, Any]:
    """Loads the main repository metadata file (`metadata.json`)."""
    metadata_path = repo_path / "metadata.json"
    if metadata_path.exists():
        return json.loads(metadata_path.read_text())
    # This should not happen after `init` but is a safe fallback.
    return {"HEAD": None, "branch": "main"}

def save_metadata(repo_path: Path, metadata: Dict[str, Any]) -> None:
    """Saves the main repository metadata file."""
    metadata_path = repo_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

# --- Index (index.json) ---

def load_index(repo_path: Path) -> Dict[str, str]:
    """Loads the staging index file (`index.json`)."""
    index_path = repo_path / "index.json"
    if index_path.exists():
        return json.loads(index_path.read_text())
    return {}

def save_index(repo_path: Path, index: Dict[str, str]) -> None:
    """Saves the staging index file."""
    index_path = repo_path / "index.json"
    index_path.write_text(json.dumps(index, indent=2))

def clear_index(repo_path: Path) -> None:
    """Clears the index by writing an empty JSON object."""
    save_index(repo_path, {})
