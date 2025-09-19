import typer
from pathlib import Path
from rich.console import Console

# Import our new, refactored storage modules
from datagit.storage import repo as repo_utils
from datagit.storage import core
from datagit.storage import metadata
from datagit.storage import repository

console = Console()
app = typer.Typer()

@app.command("add")
def add_command(file: str = typer.Argument(..., help="File to add to the staging area")):
    """
    Analyzes a file, versions it at a granular level, and stages it for commit if changed.
    """
    repo_path = repo_utils.find_repo()
    if not repo_path:
        console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
        raise typer.Exit(1)

    file_path = Path(file)
    if not file_path.exists():
        console.print(f"[red]Error: File not found at '{file_path}'[/red]")
        raise typer.Exit(1)

    # Use a relative path for consistent tracking within the repository
    repo_root = repo_path.parent
    relative_file_path = str(file_path.resolve().relative_to(repo_root.resolve()))

    console.print(f"Processing '{relative_file_path}'...")

    try:
        # 1. Construct the Merkle Tree for the file's current state.
        # This is where all the chunking and recipe creation happens.
        new_file_hash = core.construct_merkle_tree_for_file(repo_path, file_path)

        # 2. Get the file's hash from the last commit to check for changes.
        old_file_hash = repository.get_file_hash_from_last_commit(repo_path, relative_file_path)

        # 3. Compare hashes to detect changes.
        if new_file_hash == old_file_hash:
            console.print(f"[cyan]No changes detected in '{relative_file_path}'. Already up to date.[/cyan]")
            return

        # 4. If the hash is different, a change has occurred. Stage the file.
        index = metadata.load_index(repo_path)
        index[relative_file_path] = new_file_hash
        metadata.save_index(repo_path, index)

        console.print(f"[green]Staged '{relative_file_path}' for commit.[/green]")

    except IOError as e:
        console.print(f"[red]Error processing file: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        # Catch-all for other potential errors during processing
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
        raise typer.Exit(1)
