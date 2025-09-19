import hashlib
import json
from pathlib import Path
from typing import Dict, List, Any

# --- New Project Dependencies ---
# These must be installed: pip install polars pyarrow
import polars as pl
import pyarrow as pa

# --- CONFIGURATION ---
# The number of rows to include in each data chunk. Can be tuned later.
CHUNK_ROW_SIZE = 10_000

# --- CORE STORAGE FUNCTIONS ---

def hash_content(content: bytes) -> str:
    """Computes the SHA-256 hash of byte content."""
    return hashlib.sha256(content).hexdigest()

def save_object(repo_path: Path, content: bytes, obj_type: str) -> str:
    """
    Hashes content and saves it to the appropriate directory (chunks, recipes, manifests).
    This is the core of our content-addressable storage.
    Returns the hash of the content.
    """
    content_hash = hash_content(content)
    # Determine the correct directory based on the object type
    obj_dir = repo_path / obj_type
    obj_path = obj_dir / content_hash

    # Save the object only if it doesn't already exist. This is where deduplication happens.
    if not obj_path.exists():
        obj_path.write_bytes(content)

    return content_hash

# --- DATA SERIALIZATION ---

def serialize_chunk(df_chunk: pl.DataFrame) -> bytes:
    """
    Serializes a Polars DataFrame chunk into a compact binary format using Arrow IPC.
    This is much more efficient than storing chunks as CSV text.
    """
    buffer = pa.BufferOutputStream()
    # Convert Polars DataFrame to an Arrow Table and write it to the buffer
    with pa.ipc.new_stream(buffer, df_chunk.to_arrow().schema) as writer:
        writer.write(df_chunk.to_arrow())
    return buffer.getvalue().to_pybytes()

# --- MERKLE TREE CONSTRUCTION ---

def construct_merkle_tree_for_file(repo_path: Path, file_path: Path) -> str:
    """
    The main engine for Phase 1. It reads a structured file, chunks it by columns,
    builds the hierarchical recipe tree, and saves all the new objects.

    Returns the top-level file recipe hash (the file's unique fingerprint).
    """
    try:
        # For the MVP, we'll start with CSV support. More formats can be added.
        df = pl.read_csv(file_path)
    except Exception as e:
        raise IOError(f"Could not read or parse file: {file_path}. Error: {e}")

    column_recipes: List[Dict[str, str]] = []
    for column_name in df.columns:
        # 1. Create data chunks for the current column
        column_chunk_hashes: List[str] = []
        for i in range(0, df.height, CHUNK_ROW_SIZE):
            # Slice the DataFrame to get the next chunk of rows for this column
            chunk_df = df.select(column_name).slice(i, CHUNK_ROW_SIZE)
            chunk_bytes = serialize_chunk(chunk_df)
            chunk_hash = save_object(repo_path, chunk_bytes, "chunks")
            column_chunk_hashes.append(chunk_hash)

        # 2. Create the column recipe (the blueprint for a single column)
        column_recipe_data = {"chunks": column_chunk_hashes}
        # We sort keys to ensure the JSON is always serialized the same way,
        # which is critical for getting a consistent hash.
        column_recipe_content = json.dumps(column_recipe_data, sort_keys=True).encode()
        col_recipe_hash = save_object(repo_path, column_recipe_content, "recipes")
        
        column_recipes.append({"name": column_name, "recipe": col_recipe_hash})

    # 3. Create the main file recipe (the blueprint for the entire file)
    file_recipe_data = {
        "type": "columnar",
        "columns": column_recipes
    }
    file_recipe_content = json.dumps(file_recipe_data, sort_keys=True).encode()
    file_recipe_hash = save_object(repo_path, file_recipe_content, "recipes")
    
    return file_recipe_hash
