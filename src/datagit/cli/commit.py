import typer
import json
from pathlib import Path
from datetime import datetime, timezone
from rich.console import Console

# Import our refactored storage modules
from datagit.storage import repo as repo_utils
from datagit.storage import core
from datagit.storage import metadata
from datagit.storage import repository

console = Console()
app = typer.Typer()

@app.command("commit")
def commit_command(
    message: str = typer.Option(..., "-m", "--message", help="A brief message describing the changes.")
):
    """
    Records the staged changes to the repository's permanent history.
    """
    repo_path = repo_utils.find_repo()
    if not repo_path:
        console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
        raise typer.Exit(1)

    # 1. Load the staging area (index)
    index = metadata.load_index(repo_path)
    if not index:
        console.print("[yellow]Nothing to commit. Use 'datagit add <file>' to stage changes.[/yellow]")
        raise typer.Exit(1)

    # 2. Create the Directory Recipe (the master blueprint for this commit)
    dir_recipe_data = {"files": index}
    dir_recipe_content = json.dumps(dir_recipe_data, sort_keys=True).encode()
    dir_recipe_hash = core.save_object(repo_path, dir_recipe_content, "recipes")

    # 3. Get the parent commit from the current active view's HEAD
    # This now correctly reads from the refs/heads files.
    parent_commit_hash = repository.get_head_commit(repo_path)

    # 4. Create the Manifest (the commit object)
    timestamp = datetime.now(timezone.utc).isoformat()
    manifest_data = {
        "parent": parent_commit_hash,
        "message": message,
        "timestamp": timestamp,
        "recipe": dir_recipe_hash
    }
    manifest_content = json.dumps(manifest_data, sort_keys=True).encode()
    new_commit_hash = core.save_object(repo_path, manifest_content, "manifests")

    # 5. Update the current view to point to our new commit
    # This is the crucial step that moves the branch pointer forward.
    try:
        repository.update_current_view_head(repo_path, new_commit_hash)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        console.print("To save your changes, please create a new view first using 'datagit view <new-view-name>'")
        raise typer.Exit(1)

    # 6. Clear the staging area
    metadata.clear_index(repo_path)

    current_view = repository.get_current_view_name(repo_path)
    console.print(f"[green]Committed to view '{current_view}' as '{new_commit_hash[:8]}': {message}[/green]")

