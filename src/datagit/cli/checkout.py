import typer
from pathlib import Path
from rich.console import Console
from typing import Optional

# Import our storage and repository modules
from datagit.storage import repo as repo_utils
from datagit.storage import metadata
from datagit.storage import repository
from datagit.storage import core

console = Console()
app = typer.Typer()

@app.command("checkout")
def checkout_command(
    commit_hash: str = typer.Argument(..., help="The full commit hash to restore the repository state to.")
):
    """
    Restores the repository's files to the state of a specific commit.
    """
    repo_path = repo_utils.find_repo()
    if not repo_path:
        console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
        raise typer.Exit(1)

    # For safety, we should check if the index is clean. A real git would have
    # more complex checks for the working directory state.
    index = metadata.load_index(repo_path)
    if index:
        console.print("[bold red]Error: You have staged changes in your index.[/bold red]")
        console.print("Please commit your changes or clear the index before checking out a new version.")
        raise typer.Exit(1)
        
    console.print(f"Checking out commit [cyan]{commit_hash[:12]}[/cyan]...")

    # Verify that the target commit actually exists
    target_manifest = repository.get_manifest(repo_path, commit_hash)
    if not target_manifest:
        console.print(f"[red]Error: Commit '{commit_hash}' not found in the repository history.[/red]")
        raise typer.Exit(1)
        
    # Get the master blueprint (directory recipe) for the target commit
    dir_recipe_hash = target_manifest.get("recipe")
    if not dir_recipe_hash:
        console.print(f"[red]Error: Commit '{commit_hash}' is corrupted and has no data recipe.[/red]")
        raise typer.Exit(1)
        
    dir_recipe = repository.get_recipe(repo_path, dir_recipe_hash)
    if not dir_recipe:
        console.print(f"[red]Error: Could not find the main data recipe for commit '{commit_hash}'.[/red]")
        raise typer.Exit(1)

    # The core reconstruction logic will be in a new function in the core engine.
    try:
        # This function will read the directory recipe and rebuild all the files.
        core.reconstruct_working_directory(repo_path, dir_recipe)
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during file reconstruction: {e}[/bold red]")
        raise typer.Exit(1)

    # Finally, update HEAD to point to the checked-out commit
    meta = metadata.load_metadata(repo_path)
    meta["HEAD"] = commit_hash
    metadata.save_metadata(repo_path, meta)

    console.print(f"[green]Successfully checked out commit '{commit_hash[:12]}'. Your working directory is now at this state.[/green]")
