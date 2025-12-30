import typer
from pathlib import Path
import os
import json
from rich.console import Console

console = Console()
app = typer.Typer()

@app.command("init")
def init_command():
    """
    Initialize a new DataGit repository with the CADG and refs structure.
    """
    repo_path = Path(".datagit")

    if repo_path.exists():
        console.print("[yellow]Repository already initialized.[/yellow]")
        raise typer.Exit()

    # Create the repository structure
    console.print("Initializing DataGit repository...")
    os.makedirs(repo_path / "chunks", exist_ok=True)
    os.makedirs(repo_path / "recipes", exist_ok=True)
    os.makedirs(repo_path / "manifests", exist_ok=True)
    
    # --- NEW: Create the Git-like refs structure for views (branches) ---
    os.makedirs(repo_path / "refs" / "heads", exist_ok=True)

    # The first commit will be on the 'main' view. This file will store the commit hash.
    (repo_path / "refs" / "heads" / "main").write_text("")

    # --- NEW: HEAD now points to the current active view, not a commit hash ---
    # This is the standard mechanism for tracking the current branch in Git.
    (repo_path / "HEAD").write_text("ref: refs/heads/main")
    
    # Create an empty index file and schema cache
    (repo_path / "index.json").write_text(json.dumps({}, indent=2))
    (repo_path / "schemas.json").write_text(json.dumps({}, indent=2))

    console.print(f"[green]Initialized empty DataGit repository on view 'main' in {repo_path}/[/green]")

