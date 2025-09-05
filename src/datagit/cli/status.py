# src/datagit/cli/status.py

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from datagit.storage import file as storage
from datagit.storage import repo

console = Console()
app = typer.Typer()

@app.command("status")
def status_command():
    """
    Show the status of working directory, staging area, and commits.
    """
    repo_path = repo.find_repo()
    if not repo_path:
        console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
        raise typer.Exit(1)

    repo_root = repo_path.parent
    index = storage.load_index(repo_path)

    staged_files = set(index.keys())
    working_files = {
        str(p.relative_to(repo_root))
        for p in repo_root.rglob("*")
        if p.is_file() and ".datagit" not in str(p)
    }

    # --- Detect file states ---
    staged = []
    modified = []
    untracked = []

    # Check staged files (compare hash with working dir)
    for rel_path, entry in index.items():
        file_path = repo_root / rel_path
        if not file_path.exists():
            continue  # deleted case, can extend later
        current_hash = storage.hash_file(file_path)
        if current_hash != entry["hash"]:
            modified.append(rel_path)
        else:
            staged.append(rel_path)

    # Untracked: in working dir but not staged
    for rel_path in working_files - staged_files:
        untracked.append(rel_path)

    # --- Display results ---
    if not staged and not modified and not untracked:
        console.print("[green]Nothing to commit, working tree clean.[/green]")
        return

    if staged:
        console.print("[cyan]Staged files:[/cyan]")
        for f in staged:
            console.print(f"  {f}")

    if modified:
        console.print("[yellow]Modified (not staged):[/yellow]")
        for f in modified:
            console.print(f"  {f}")

    if untracked:
        console.print("[magenta]Untracked files:[/magenta]")
        for f in untracked:
            console.print(f"  {f}")
