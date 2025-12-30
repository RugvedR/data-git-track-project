import json
from pathlib import Path
from typing import Dict, Any, Optional

# The 'metadata' import is no longer needed for resolving the current commit,
# but we will keep it for its other utility functions like managing the index.
from datagit.storage import metadata
from rich.console import Console

# It's good practice to have a console object available for potential errors.
console = Console()

def get_object(repo_path: Path, obj_hash: str, obj_type: str) -> Optional[bytes]:
    """Reads an object's content from storage by its hash."""
    obj_dir_name = f"{obj_type.rstrip('s')}s"
    obj_dir = repo_path / obj_dir_name
    obj_path = obj_dir / obj_hash
    if obj_path.exists():
        return obj_path.read_bytes()
    return None

def get_recipe(repo_path: Path, recipe_hash: str) -> Optional[Dict[str, Any]]:
    """Retrieves and deserializes a recipe object."""
    content = get_object(repo_path, recipe_hash, "recipe")
    if content:
        return json.loads(content)
    return None

def get_manifest(repo_path: Path, manifest_hash: str) -> Optional[Dict[str, Any]]:
    """Retrieves and deserializes a manifest object."""
    content = get_object(repo_path, manifest_hash, "manifest")
    if content:
        return json.loads(content)
    return None

# --- NEW STATE MANAGEMENT FUNCTIONS ---

def get_current_view_name(repo_path: Path) -> Optional[str]:
    """
    Reads the HEAD file to find the name of the current active view (branch).
    """
    head_file = repo_path / "HEAD"
    if not head_file.exists():
        return None
    content = head_file.read_text().strip()
    # Content is expected to be in the format: "ref: refs/heads/main"
    if content.startswith("ref: "):
        # Returns just "main"
        return content.split("/")[-1]
    # If it's not a ref, we are in a detached state.
    return None

def get_head_commit(repo_path: Path) -> Optional[str]:
    """
    Finds the commit hash that HEAD points to, whether it's a direct commit
    (detached HEAD) or a reference to a view (branch).
    """
    head_file = repo_path / "HEAD"
    if not head_file.exists():
        return None
    
    content = head_file.read_text().strip()
    
    if content.startswith("ref: "):
        # It's a reference to a view, e.g., "ref: refs/heads/main"
        ref_path = repo_path / content.split(" ", 1)[1]
        if ref_path.exists():
            commit_hash = ref_path.read_text().strip()
            return commit_hash if commit_hash else None
    elif len(content) == 64:
        # It's a raw SHA-256 hash, indicating a detached HEAD state.
        return content
        
    return None

def update_current_view_head(repo_path: Path, commit_hash: str):
    """
    Updates the file for the current active view to point to the new commit hash.
    This is the core action of making a commit on a branch.
    """
    view_name = get_current_view_name(repo_path)
    if not view_name:
        # This prevents writing commits when in a detached HEAD state.
        raise RuntimeError("Cannot update view head: You are in a 'detached HEAD' state.")
        
    view_file = repo_path / "refs" / "heads" / view_name
    view_file.write_text(commit_hash)

def get_file_hash_from_last_commit(repo_path: Path, file_path: str) -> Optional[str]:
    """
    Finds the recipe hash for a specific file as it was in the last commit
    of the currently active view (HEAD).
    """
    head_commit_hash = get_head_commit(repo_path)
    if not head_commit_hash:
        return None # No commits in this view yet.

    last_manifest = get_manifest(repo_path, head_commit_hash)
    if not last_manifest: return None
    
    dir_recipe_hash = last_manifest.get("recipe")
    if not dir_recipe_hash: return None
        
    dir_recipe = get_recipe(repo_path, dir_recipe_hash)
    if not dir_recipe: return None

    # The directory recipe's 'files' key holds the mapping from file path to file recipe hash.
    return dir_recipe.get("files", {}).get(file_path)

