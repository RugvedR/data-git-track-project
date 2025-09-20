import hashlib
import json
from pathlib import Path
from typing import Dict, List, Any

# --- New Project Dependencies ---
# These must be installed: pip install polars pyarrow.
# Polars is chosen for its exceptional speed and memory efficiency in processing
# large dataframes, which is critical for the chunking logic.
# PyArrow provides access to the Apache Arrow columnar format, an industry
# standard for efficient, language-agnostic data serialization.
import polars as pl
import pyarrow as pa

# Import metadata helpers to access the new schema cache functions
from datagit.storage import metadata

# --- CONFIGURATION ---
# The number of rows to include in each data chunk. This value represents a
# critical trade-off:
#   - A smaller size (e.g., 1,000) offers higher granularity, meaning small
#     changes result in smaller data transfers, but creates more metadata objects to manage.
#   - A larger size (e.g., 100,000) reduces metadata overhead but is less
#     efficient for small, scattered changes.
# 10,000 is a balanced default for many common use cases.
CHUNK_ROW_SIZE = 10_000

# --- CORE STORAGE FUNCTIONS ---

def hash_content(content: bytes) -> str:
    """
    Computes the SHA-256 hash of byte content, providing a unique and
    verifiable "fingerprint" for any piece of data. This is the foundation
    of our content-addressable storage model.
    """
    return hashlib.sha256(content).hexdigest()

def save_object(repo_path: Path, content: bytes, obj_type_dir: str) -> str:
    """
    Hashes content and saves it to the appropriate directory (chunks, recipes, manifests).
    This function is the heart of our content-addressable storage model. It ensures
    that any piece of content is stored only once, providing universal deduplication.
    
    Returns the unique hash of the content.
    """
    content_hash = hash_content(content)
    # Directly use the provided directory name (e.g., "chunks").
    obj_dir = repo_path / obj_type_dir
    obj_path = obj_dir / content_hash

    # Save the object only if a file with its hash doesn't already exist.
    # This `if` condition is the critical step where all data deduplication occurs.
    # If the content has been seen before, its hash will match an existing file,
    # and this write operation is skipped entirely, saving both time and storage.
    if not obj_path.exists():
        # This print statement provides valuable insight during debugging, showing
        # exactly which new objects are being physically written to disk.
        print(f"  -> Saving new {obj_type_dir.rstrip('s')} object: {content_hash[:12]}")
        obj_path.write_bytes(content)
    # else:
    #     print(f"  -> Skipping duplicate {obj_type_dir.rstrip('s')} object: {content_hash[:12]}")

    return content_hash

# --- DATA SERIALIZATION ---

def serialize_chunk(df_chunk: pl.DataFrame, schema: pa.Schema) -> bytes:
    """
    Serializes a Polars DataFrame chunk into the highly efficient Arrow IPC stream format.
    Using a standardized binary format is significantly faster and more space-efficient
    than storing intermediate data as text (like mini-CSVs).
    
    Crucially, it requires a consistent schema to be passed in. This ensures that
    the binary output is deterministic, meaning the same data will always produce
    the exact same byte stream and, therefore, the same hash. Without this,
    deduplication would fail.
    """
    buffer = pa.BufferOutputStream()
    # The schema provided here acts as a strict contract for serialization,
    # overriding any schema inference that might occur on the chunk itself.
    with pa.ipc.new_stream(buffer, schema) as writer:
        writer.write(df_chunk.to_arrow())
    return buffer.getvalue().to_pybytes()

# --- MERKLE TREE CONSTRUCTION ---

def construct_merkle_tree_for_file(repo_path: Path, file_path: Path, relative_file_path: str) -> str:
    """
    The main engine for Phase 1. This function orchestrates the entire versioning
    process for a single file. It reads a structured file using a cached schema,
    breaks it down column by column into versioned chunks, and then builds the
    hierarchical tree of recipes that provides its unique, verifiable fingerprint.

    Returns the top-level file recipe hash.
    """
    schemas = metadata.load_schemas(repo_path)
    cached_schema_info = schemas.get(relative_file_path)

    try:
        if cached_schema_info:
            # If a schema is cached, we use it to construct a dictionary of dtypes.
            # This is the most direct and robust way to enforce a schema during a read.
            polars_dtypes = {k: getattr(pl, v) for k, v in cached_schema_info.items()}
            df = pl.read_csv(file_path, dtypes=polars_dtypes)
        else:
            # First time seeing this file: perform a one-time inference to establish the schema.
            df = pl.read_csv(file_path)
            
            # Cache the determined schema so we never have to infer it again for this file.
            # This makes subsequent runs both faster and perfectly deterministic.
            polars_schema_to_cache = {name: str(dtype) for name, dtype in df.schema.items()}
            schemas[relative_file_path] = polars_schema_to_cache
            metadata.save_schemas(repo_path, schemas)

    except Exception as e:
        raise IOError(f"Could not read or parse file: {file_path}. Error: {e}")

    # Convert the final, typed DataFrame schema to the Arrow format for serialization.
    arrow_schema = df.to_arrow().schema

    column_recipes: List[Dict[str, str]] = []
    # Process columns in a sorted order to ensure the final file recipe is always
    # constructed identically, which is vital for a stable top-level hash.
    for column_name in sorted(df.columns):
        # 1. Create data chunks for the current column
        column_chunk_hashes: List[str] = []
        column_field = arrow_schema.field(column_name)
        field_schema = pa.schema([column_field])

        for i in range(0, df.height, CHUNK_ROW_SIZE):
            chunk_df = df.select(column_name).slice(i, CHUNK_ROW_SIZE)
            chunk_bytes = serialize_chunk(chunk_df, field_schema)
            chunk_hash = save_object(repo_path, chunk_bytes, "chunks")
            column_chunk_hashes.append(chunk_hash)

        # 2. Create the column recipe (a blueprint listing chunk hashes in order)
        column_recipe_data = {"chunks": column_chunk_hashes}
        # Sorting keys ensures that the JSON output is identical for identical data.
        column_recipe_content = json.dumps(column_recipe_data, sort_keys=True).encode()
        col_recipe_hash = save_object(repo_path, column_recipe_content, "recipes")
        
        column_recipes.append({"name": column_name, "recipe": col_recipe_hash})

    # 3. Create the main file recipe (a blueprint mapping columns to their recipes)
    sorted_column_recipes = sorted(column_recipes, key=lambda x: x['name'])
    file_recipe_data = {
        "type": "columnar",
        "columns": sorted_column_recipes
    }
    file_recipe_content = json.dumps(file_recipe_data, sort_keys=True).encode()
    file_recipe_hash = save_object(repo_path, file_recipe_content, "recipes")
    
    return file_recipe_hash

