import json
from pathlib import Path
from typing import Dict, Any, Optional

from datagit.storage import metadata

def get_object(repo_path: Path, obj_hash: str, obj_type: str) -> Optional[bytes]:
    """Reads an object's content from storage by its hash."""
    obj_dir = repo_path / f"{obj_type}s" # e.g., chunks, recipes, manifests
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

def get_file_hash_from_last_commit(repo_path: Path, file_path: str) -> Optional[str]:
    """
    Finds the recipe hash for a specific file as it was in the last commit (HEAD).
    Returns None if the file didn't exist in the last commit or if there are no commits.
    """
    meta = metadata.load_metadata(repo_path)
    head_commit_hash = meta.get("HEAD")
    if not head_commit_hash:
        return None

    # Traverse the recipes to find the file
    last_manifest = get_manifest(repo_path, head_commit_hash)
    if not last_manifest:
        return None

    dir_recipe_hash = last_manifest.get("recipe")
    if not dir_recipe_hash:
        return None
        
    dir_recipe = get_recipe(repo_path, dir_recipe_hash)
    if not dir_recipe:
        return None

    # The directory recipe's 'files' key holds the mapping
    return dir_recipe.get("files", {}).get(file_path)
