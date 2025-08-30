# src/datagit/cli/add.py
import typer
from pathlib import Path
import os
import shutil
from rich.console import Console

console = Console()
app = typer.Typer()

@app.command("add")
def add_command(file: str = typer.Argument(..., help="File to add to staging area")):
    """
    Add a file to the DataGit staging area.
    """
    repo_path = Path(".datagit")

    if not repo_path.exists():
        console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
        raise typer.Exit(1)

    staging_path = repo_path / "staging"
    staging_path.mkdir(exist_ok=True)

    file_path = Path(file)
    if not file_path.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    # Copy file into staging area
    dest = staging_path / file_path.name
    shutil.copy(file_path, dest)

    console.print(f"[green]Added {file} to staging area.[/green]")
