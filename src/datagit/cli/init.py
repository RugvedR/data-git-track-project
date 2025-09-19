# src/datagit/cli/init.py
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
    Initialize a new DataGit repository with the CADG structure.
    """
    repo_path = Path(".datagit")

    if repo_path.exists():
        console.print("[yellow]Repository already initialized.[/yellow]")
        raise typer.Exit()

    # Create the new repository structure for the CADG model
    console.print("Initializing DataGit repository...")
    os.makedirs(repo_path / "chunks", exist_ok=True)
    os.makedirs(repo_path / "recipes", exist_ok=True)
    os.makedirs(repo_path / "manifests", exist_ok=True)

    # Initial metadata with HEAD pointing to null
    metadata = {
        "HEAD": None,
        "branch": "main"
    }
    (repo_path / "metadata.json").write_text(json.dumps(metadata, indent=2))
    
    # Create an empty index file
    (repo_path / "index.json").write_text(json.dumps({}, indent=2))

    console.print(f"[green]Initialized empty DataGit repository in {repo_path}/[/green]")