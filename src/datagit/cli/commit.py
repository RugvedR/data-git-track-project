import typer
from pathlib import Path
import json
from datetime import datetime
from rich.console import Console
from datagit.storage import file as storage

console = Console()
app = typer.Typer()

@app.command("commit")
def commit_command(
    message: str = typer.Option(..., "-m", "--message", help="Commit message")
):
    """
    Commit staged changes in the DataGit repository.
    """
    repo_path = Path(".datagit")
    metadata_path = repo_path / "metadata.json"
    commits_dir = repo_path / "commits"

    if not repo_path.exists():
        console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
        raise typer.Exit(1)

    # Load index (staged changes)
    index = storage.load_index(repo_path)
    if not index:
        console.print("[yellow]Nothing staged. Use 'datagit add <file>' first.[/yellow]")
        raise typer.Exit(1)

    # Load metadata
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
    else:
        metadata = {"HEAD": None, "branch": "main", "commits": []}

    # Generate commit ID
    commit_id = str(len(metadata["commits"]) + 1).zfill(4)  # e.g., "0001"

    commit_data = {
        "id": commit_id,
        "message": message,
        "files": index.copy(),  # snapshot of staged files
        "parent": metadata["HEAD"],
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Save commit file
    commits_dir.mkdir(exist_ok=True)
    commit_file = commits_dir / f"{commit_id}.json"
    commit_file.write_text(json.dumps(commit_data, indent=2))

    # Update metadata
    metadata["HEAD"] = commit_id
    metadata["commits"].append(commit_id)
    metadata_path.write_text(json.dumps(metadata, indent=2))

    # Clear staging (index.json)
    storage.save_index(repo_path, {})

    console.print(f"[green]Committed as {commit_id}: {message}[/green]")
