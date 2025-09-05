# src/datagit/cli/init.py
import typer
from pathlib import Path
import os
import json
from rich.console import Console

console = Console()
app = typer.Typer()  # sub-app, later plugged into main

@app.command("init")
def init_command():
    """
    Initialize a new DataGit repository.
    """
    repo_path = Path(".datagit")

    if repo_path.exists():
        console.print("[yellow]Repository already initialized.[/yellow]")
        return

    # Create repo structure
    os.makedirs(repo_path / "objects", exist_ok=True)
    os.makedirs(repo_path / "commits", exist_ok=True)

    metadata = {
        "HEAD": None,
        "branch": "main",
        "commits": []
    }
    (repo_path / "metadata.json").write_text(json.dumps(metadata, indent=2))

    console.print("[green]Initialized empty DataGit repository in .datagit/[/green]")
