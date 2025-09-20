import typer
from pathlib import Path
from rich.console import Console
from typing import Optional

# Import our storage and repository modules
from datagit.storage import repo as repo_utils
from datagit.storage import repository

console = Console()
app = typer.Typer()

@app.command("view")
def view_command(
    view_name: Optional[str] = typer.Argument(None, help="The name of the view to create."),
    start_point: Optional[str] = typer.Option(None, "-c", "--commit", help="A specific commit hash to start the new view from. Defaults to the current HEAD.")
):
    """
    Create a new view or list all existing views.
    A 'view' is an independent line of development, similar to a branch in Git.
    """
    repo_path = repo_utils.find_repo()
    if not repo_path:
        console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
        raise typer.Exit(1)

    refs_heads_path = repo_path / "refs" / "heads"

    # If no view name is provided, list all existing views.
    if not view_name:
        console.print("[bold]Available views:[/bold]")
        current_view = repository.get_current_branch_name(repo_path)
        for view_file in sorted(refs_heads_path.iterdir()):
            if view_file.name == current_view:
                console.print(f"  [bold green]* {view_file.name}[/bold green]")
            else:
                console.print(f"    {view_file.name}")
        return

    # If a view name is provided, create a new view.
    new_view_file = refs_heads_path / view_name
    if new_view_file.exists():
        console.print(f"[red]Error: A view named '{view_name}' already exists.[/red]")
        raise typer.Exit(1)

    commit_to_point_to = start_point
    if not commit_to_point_to:
        # If no specific commit is given, create the view from the current HEAD.
        commit_to_point_to = repository.get_head_commit(repo_path)

    if not commit_to_point_to:
        console.print("[yellow]Cannot create view: The repository has no commits yet.[/yellow]")
        raise typer.Exit(1)

    # Create the new view file and write the commit hash into it.
    new_view_file.write_text(commit_to_point_to)
    console.print(f"Created new view [cyan]'{view_name}'[/cyan] pointing to commit [cyan]{commit_to_point_to[:12]}[/cyan].")
    console.print(f"To make it active, run: [bold]datagit activate {view_name}[/bold]")

