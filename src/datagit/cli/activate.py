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

@app.command("activate")
def activate_command(
    view_or_commit: str = typer.Argument(..., help="The view (branch) name or a specific commit hash to activate.")
):
    """
    Activates a specific data view or restores the working directory to a historical commit.
    """
    repo_path = repo_utils.find_repo()
    if not repo_path:
        console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
        raise typer.Exit(1)

    index = metadata.load_index(repo_path)
    if index:
        console.print("[bold red]Error: You have staged changes.[/bold red]")
        console.print("Please commit your changes before activating a new version.")
        raise typer.Exit(1)
        
    commit_hash_to_activate = None
    
    # Check if the user provided a view (branch) name
    view_file = repo_path / "refs" / "heads" / view_or_commit
    if view_file.exists():
        console.print(f"Activating view [cyan]'{view_or_commit}'[/cyan]...")
        commit_hash_to_activate = view_file.read_text().strip()
        # Update HEAD to point to the view, which is the standard way of working.
        (repo_path / "HEAD").write_text(f"ref: refs/heads/{view_or_commit}")
    else:
        # If it's not a view, assume it's a commit hash and enter a "detached HEAD" state.
        console.print(f"Activating historical commit [cyan]{view_or_commit[:12]}[/cyan]...")
        console.print("[yellow]Warning: You are in a 'detached' state.[/yellow]")
        console.print("You can look around and make experimental changes, but they are not part of any view.")
        commit_hash_to_activate = view_or_commit
        # Update HEAD to point directly to the commit hash.
        (repo_path / "HEAD").write_text(commit_hash_to_activate)

    if not commit_hash_to_activate:
        console.print(f"[yellow]View '{view_or_commit}' is empty. Nothing to activate.[/yellow]")
        return

    target_manifest = repository.get_manifest(repo_path, commit_hash_to_activate)
    if not target_manifest:
        console.print(f"[red]Error: Commit '{commit_hash_to_activate}' not found.[/red]")
        raise typer.Exit(1)
        
    dir_recipe_hash = target_manifest.get("recipe")
    if not dir_recipe_hash:
        console.print(f"[red]Error: Commit '{commit_hash_to_activate}' is corrupted.[/red]")
        raise typer.Exit(1)
        
    dir_recipe = repository.get_recipe(repo_path, dir_recipe_hash)
    if not dir_recipe:
        console.print(f"[red]Error: Could not find data recipe for commit '{commit_hash_to_activate}'.[/red]")
        raise typer.Exit(1)

    try:
        core.reconstruct_working_directory(repo_path, dir_recipe)
    except Exception as e:
        # This includes handling file lock errors on Windows.
        console.print(f"[bold red]An error occurred during file reconstruction: {e}[/bold red]")
        console.print("Please ensure the files to be overwritten are not open in another application.")
        raise typer.Exit(1)

    console.print(f"[green]Successfully activated version '{commit_hash_to_activate[:12]}'.[/green]")
