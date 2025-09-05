import typer
from pathlib import Path
from rich.console import Console
from datagit.storage import file as storage

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

    file_path = Path(file)
    if not file_path.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    # Compute hash + save object
    file_hash = storage.hash_file(file_path)
    storage.save_object(file_path, file_hash, repo_path)

    # Load and update index
    index = storage.load_index(repo_path)
    index[str(file_path)] = file_hash
    storage.save_index(repo_path, index)

    console.print(f"[green]Staged {file} ({file_hash[:8]})[/green]")
