import hashlib
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
import struct

# --- New Project Dependencies ---
# These must be installed: pip install polars pyarrow.
import polars as pl
import pyarrow as pa

# Import metadata helpers to access the new schema cache functions
from datagit.storage import metadata, repository
from rich.console import Console

console = Console()

# --- CONFIGURATION ---
CHUNK_ROW_SIZE = 10_000

# --- CORE STORAGE FUNCTIONS ---

def hash_content(content: bytes) -> str:
    """Computes the SHA-256 hash of byte content for recipes and manifests."""
    return hashlib.sha256(content).hexdigest()

def save_object(repo_path: Path, content: bytes, obj_type_dir: str) -> str:
    """Hashes and saves non-chunk objects like recipes and manifests."""
    content_hash = hash_content(content)
    obj_dir = repo_path / obj_type_dir
    obj_path = obj_dir / content_hash

    if not obj_path.exists():
        console.log(f"[yellow]  -> Saving new {obj_type_dir.rstrip('s')} object:[/yellow] [cyan]{content_hash[:12]}[/cyan]")
        obj_path.write_bytes(content)
    return content_hash

# --- CANONICAL DATA SERIALIZATION & HASHING ---

def get_canonical_bytes_and_hash(series: pl.Series) -> Tuple[bytes, str]:
    """
    This is the definitive engine for both hashing and storage. It first converts
    the complex Series object to a simple list of Python primitives, then creates a
    stable, canonical binary representation. This guarantees perfect determinism.
    """
    hasher = hashlib.sha256()
    byte_parts = []
    
    name_bytes = series.name.encode('utf-8')
    dtype_bytes = str(series.dtype).encode('utf-8')
    byte_parts.extend([name_bytes, dtype_bytes])

    values_as_primitives = series.to_list()

    for value in values_as_primitives:
        if value is None:
            part = b'\x00\x00NULL\x00\x00'
        elif isinstance(value, str):
            part = value.encode('utf-8')
        elif isinstance(value, int):
            part = value.to_bytes(8, byteorder='big', signed=True)
        elif isinstance(value, float):
            part = struct.pack('>d', value)
        else:
            part = str(value).encode('utf-8')
        byte_parts.append(part)

    full_byte_stream = b'\x01'.join(byte_parts)
    content_hash = hashlib.sha256(full_byte_stream).hexdigest()

    return full_byte_stream, content_hash

def save_chunk_if_needed(repo_path: Path, chunk_hash: str, chunk_content: bytes):
    """
    Saves the chunk content to storage, using the pre-computed deterministic hash
    as the filename.
    """
    obj_path = repo_path / "chunks" / chunk_hash
    if not obj_path.exists():
        console.log(f"[yellow]  -> Saving new chunk object:[/yellow] [cyan]{chunk_hash[:12]}[/cyan]")
        obj_path.write_bytes(chunk_content)

# --- MERKLE TREE CONSTRUCTION (for `add`) ---

def construct_merkle_tree_for_file(repo_path: Path, file_path: Path, relative_file_path: str) -> str:
    """The main engine for Phase 1, re-architected for perfect determinism."""
    console.rule(f"[bold blue]Constructing Merkle Tree for '{relative_file_path}'")

    schemas = metadata.load_schemas(repo_path)
    cached_schema_info = schemas.get(relative_file_path)

    try:
        if cached_schema_info:
            polars_dtypes = {k: getattr(pl, v) for k, v in cached_schema_info.items()}
            df = pl.read_csv(file_path, dtypes=polars_dtypes, ignore_errors=True)
        else:
            df = pl.read_csv(file_path, ignore_errors=True)
            polars_schema_to_cache = {name: str(dtype) for name, dtype in df.schema.items()}
            schemas[relative_file_path] = polars_schema_to_cache
            metadata.save_schemas(repo_path, schemas)

    except Exception as e:
        raise IOError(f"Could not read or parse file: {file_path}. Error: {e}")

    # --- FIX: Store the original column order ---
    # We capture the exact column order from the DataFrame as it was read.
    original_column_order = df.columns
    
    console.log("[bold]Processing Columns[/bold]")
    column_recipes: List[Dict[str, str]] = []
    
    # We still sort the columns before processing. This is critical to ensure
    # the final file recipe hash is deterministic. The sort order here is
    # ONLY for calculating the hash, not for storing the structure.
    for column_name in sorted(df.columns):
        column_chunk_hashes: List[str] = []
        for i in range(0, df.height, CHUNK_ROW_SIZE):
            chunk_series = df.select(column_name).slice(i, CHUNK_ROW_SIZE).to_series()
            chunk_content_for_storage, chunk_hash = get_canonical_bytes_and_hash(chunk_series)
            save_chunk_if_needed(repo_path, chunk_hash, chunk_content_for_storage)
            column_chunk_hashes.append(chunk_hash)

        column_recipe_data = {"chunks": column_chunk_hashes}
        column_recipe_content = json.dumps(column_recipe_data, sort_keys=True).encode()
        col_recipe_hash = save_object(repo_path, column_recipe_content, "recipes")
        
        column_recipes.append({"name": column_name, "recipe": col_recipe_hash})

    # The list of columns for the recipe is also sorted to ensure a stable hash.
    sorted_column_recipes = sorted(column_recipes, key=lambda x: x['name'])
    
    file_recipe_data = {
        "type": "columnar",
        # --- FIX: Add the original, unsorted order to the recipe ---
        "column_order": original_column_order,
        "columns": sorted_column_recipes
    }
    file_recipe_content = json.dumps(file_recipe_data, sort_keys=True).encode()
    file_recipe_hash = save_object(repo_path, file_recipe_content, "recipes")
    
    console.rule(f"[bold green]Final File Recipe Hash: {file_recipe_hash}")
    return file_recipe_hash

# --- DATA RECONSTRUCTION (for `checkout` / `activate`) ---

def deserialize_chunk_from_storage(chunk_content: bytes) -> pl.Series:
    """
    The inverse of `get_canonical_bytes_and_hash`. It reads our custom binary
    format from a chunk file and reconstructs it into a Polars Series.
    """
    byte_parts = chunk_content.split(b'\x01')
    col_name = byte_parts[0].decode('utf-8')
    dtype_str = byte_parts[1].decode('utf-8')
    raw_values = byte_parts[2:]

    polars_dtype = getattr(pl, dtype_str)
    values = []
    for val_bytes in raw_values:
        if val_bytes == b'\x00\x00NULL\x00\x00':
            values.append(None)
        elif polars_dtype == pl.String:
            values.append(val_bytes.decode('utf-8'))
        elif polars_dtype == pl.Int64:
            values.append(int.from_bytes(val_bytes, byteorder='big', signed=True))
        elif polars_dtype == pl.Float64:
            values.append(struct.unpack('>d', val_bytes)[0])
        else:
            values.append(val_bytes.decode('utf-8')) # Fallback
            
    return pl.Series(name=col_name, values=values, dtype=polars_dtype)

def reconstruct_file_from_recipe(repo_path: Path, repo_root: Path, file_path_str: str, file_recipe: Dict[str, Any]):
    """Rebuilds a single file from its versioned chunks."""
    all_columns_data = []
    
    for col_info in file_recipe["columns"]:
        col_recipe_hash = col_info["recipe"]
        col_recipe = repository.get_recipe(repo_path, col_recipe_hash)
        
        column_chunks = []
        for chunk_hash in col_recipe["chunks"]:
            chunk_content = repository.get_object(repo_path, chunk_hash, "chunk")
            if chunk_content:
                chunk_series = deserialize_chunk_from_storage(chunk_content)
                column_chunks.append(chunk_series)
        
        if column_chunks:
            full_column = pl.concat(column_chunks)
            all_columns_data.append(full_column)

    if all_columns_data:
        df = pl.DataFrame(all_columns_data)
        
        # --- FIX: Use the stored column order to reconstruct the file correctly ---
        # We retrieve the original column order from the recipe.
        original_order = file_recipe.get("column_order")
        if original_order:
            # Reorder the DataFrame columns to match the original file.
            df = df.select(original_order)
        
        output_path = repo_root / file_path_str
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.write_csv(output_path)
        console.log(f"  -> Reconstructed file [green]'{file_path_str}'[/green]")

def reconstruct_working_directory(repo_path: Path, dir_recipe: Dict[str, Any]):
    """
    The main reconstruction engine. It iterates through a directory recipe and
    rebuilds all the files it describes, overwriting the user's working directory.
    """
    repo_root = repo_path.parent
    files_to_reconstruct = dir_recipe.get("files", {})

    console.log("[bold]Reconstructing files from commit...[/bold]")
    for file_path_str, file_recipe_hash in files_to_reconstruct.items():
        file_recipe = repository.get_recipe(repo_path, file_recipe_hash)
        if file_recipe:
            reconstruct_file_from_recipe(repo_path, repo_root, file_path_str, file_recipe)
        else:
            console.log(f"[red]Warning: Could not find recipe '{file_recipe_hash}' for file '{file_path_str}'. Skipping.[/red]")

