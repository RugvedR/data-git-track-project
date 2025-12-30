import typer
import os
from pathlib import Path
from rich.console import Console

# Import the modern architecture modules
from datagit.storage import repo as repo_utils
from datagit.storage import metadata
from datagit.storage import repository
from datagit.storage import core

console = Console()
app = typer.Typer()

def get_all_files(root_path: Path, ignore_dirs: list = None):
    """
    Recursively finds all files in the repository to capture the 'Working Directory' state.
    """
    if ignore_dirs is None:
        ignore_dirs = [".datagit", ".git", "__pycache__", ".DS_Store"]
        
    all_files = []
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file.startswith("."): continue
            full_path = Path(root) / file
            rel_path = str(full_path.relative_to(root_path))
            all_files.append(rel_path)
    return set(all_files)

@app.command("status")
def status_command():
    """
    Show the working tree status: staged changes, modified files, and untracked files.
    """
    repo_path = repo_utils.find_repo()
    if not repo_path:
        console.print("[red]No DataGit repository found.[/red]")
        raise typer.Exit(1)

    repo_root = repo_path.parent

    # --- 1. LOAD THE THREE STATES ---

    # State A: Staging Area (Index)
    index = metadata.load_index(repo_path)

    # State B: HEAD Commit (The "Truth" of history)
    head_files = {}
    head_commit = repository.get_head_commit(repo_path)
    if head_commit:
        manifest = repository.get_manifest(repo_path, head_commit)
        if manifest:
            recipe_hash = manifest.get("recipe")
            if recipe_hash:
                dir_recipe = repository.get_recipe(repo_path, recipe_hash)
                if dir_recipe:
                    head_files = dir_recipe.get("files", {})

    # State C: Working Directory (Current Reality)
    working_files = get_all_files(repo_root)

    # --- 2. COMPARE STATES ---
    
    staged_changes = []       # Index != HEAD
    unstaged_changes = []     # Workspace != Index (or HEAD)
    untracked_files = []      # Workspace not in Index AND not in HEAD
    deleted_files = []        # In Index/HEAD but missing from Workspace

    with console.status("[bold green]Scanning workspace...[/bold green]"):
        # A. Check Working Directory vs. Known State
        for file_path_str in working_files:
            
            # Determine if we need to calculate the hash.
            # Optimization: If it's untracked, we don't strictly *need* the hash yet,
            # but to check modification we do.
            is_tracked = (file_path_str in index) or (file_path_str in head_files)
            
            if not is_tracked:
                untracked_files.append(file_path_str)
                continue

            # It is tracked. We must hash it to see if it changed.
            try:
                # Use the core engine to get the deterministic hash
                file_path = repo_root / file_path_str
                current_hash = core.construct_merkle_tree_for_file(repo_path, file_path, file_path_str)
            except Exception:
                console.print(f"[yellow]Warning: Could not read '{file_path_str}'[/yellow]")
                continue

            # Compare logic
            if file_path_str in index:
                # If in index, compare against index (Staging area takes precedence)
                if current_hash != index[file_path_str]:
                    unstaged_changes.append(file_path_str)
            elif file_path_str in head_files:
                # If NOT in index, compare against HEAD
                if current_hash != head_files[file_path_str]:
                    unstaged_changes.append(file_path_str)
                # Else: It matches HEAD, so it is "Clean".

        # B. Check for Deleted Files & Staged Changes
        # We look at everything we *expect* to exist (from Index or HEAD)
        all_tracked = set(index.keys()) | set(head_files.keys())
        
        for file_path_str in all_tracked:
            if file_path_str not in working_files:
                deleted_files.append(file_path_str)
                continue
            
            # Check Staged Status (Index vs HEAD)
            # Something is staged if it's in the index...
            if file_path_str in index:
                # ...and it's either NEW (not in HEAD) or DIFFERENT from HEAD
                if file_path_str not in head_files:
                    staged_changes.append(f"new file:   {file_path_str}")
                elif index[file_path_str] != head_files[file_path_str]:
                    staged_changes.append(f"modified:   {file_path_str}")

    # --- 3. DISPLAY RESULTS ---
    
    current_view = repository.get_current_view_name(repo_path)
    console.print(f"On branch [bold cyan]{current_view}[/bold cyan]\n")

    has_changes = False

    if staged_changes:
        has_changes = True
        console.print("[green]Changes to be committed:[/green]")
        for item in staged_changes:
            console.print(f"    [green]{item}[/green]")
        console.print("")

    if unstaged_changes:
        has_changes = True
        console.print("[yellow]Changes not staged for commit:[/yellow]")
        console.print("  (use \"datagit add <file>...\" to update what will be committed)")
        for item in unstaged_changes:
            console.print(f"    [yellow]modified:   {item}[/yellow]")
        console.print("")

    if deleted_files:
        has_changes = True
        console.print("[red]Deleted files:[/red]")
        for item in deleted_files:
            console.print(f"    [red]deleted:    {item}[/red]")
        console.print("")

    if untracked_files:
        has_changes = True
        console.print("[red]Untracked files:[/red]")
        console.print("  (use \"datagit add <file>...\" to include in what will be committed)")
        for item in untracked_files:
            console.print(f"    [red]{item}[/red]")
        console.print("")

    if not has_changes:
        console.print("nothing to commit, working tree clean")