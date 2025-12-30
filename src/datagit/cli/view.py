import typer
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

    # --- LIST MODE ---
    # We only list if NO name is provided.
    if not view_name:
        # BUG FIX 1: If user provided a commit hash but NO name, that's an error.
        if start_point:
            console.print("[red]Error: You must provide a View Name to create a new view.[/red]")
            console.print(f"Usage: [bold]datagit view <new-view-name> -c {start_point}[/bold]")
            raise typer.Exit(1)

        console.print("[bold]Available views:[/bold]")
        
        # BUG FIX 2: Corrected function name from 'get_current_branch_name' to 'get_current_view_name'
        current_view = repository.get_current_view_name(repo_path)
        
        if refs_heads_path.exists():
            # Sort views alphabetically for clean display
            views = sorted([f for f in refs_heads_path.iterdir() if f.is_file()])
            
            if not views:
                console.print("  [yellow](No views created yet)[/yellow]")
                
            for view_file in views:
                if view_file.name == current_view:
                    console.print(f"  [bold green]* {view_file.name}[/bold green]")
                else:
                    console.print(f"    {view_file.name}")
        return

    # --- CREATE MODE ---
    new_view_file = refs_heads_path / view_name
    if new_view_file.exists():
        console.print(f"[red]Error: A view named '{view_name}' already exists.[/red]")
        raise typer.Exit(1)

    # Determine the commit hash for the new view
    commit_to_point_to = start_point
    
    if not commit_to_point_to:
        # Default: Use the current HEAD
        commit_to_point_to = repository.get_head_commit(repo_path)

    # Validation: Ensure we have a valid commit hash
    if not commit_to_point_to:
        console.print("[yellow]Cannot create view: The repository has no commits yet.[/yellow]")
        console.print("Make your first commit on 'main' before creating new views.")
        raise typer.Exit(1)
        
    # Validation: If the user manually provided a hash, verify it exists
    if start_point:
        manifest = repository.get_manifest(repo_path, start_point)
        if not manifest:
            console.print(f"[red]Error: Target commit '{start_point}' not found in history.[/red]")
            raise typer.Exit(1)

    # Perform the Action: Write the commit hash to the new view file
    new_view_file.write_text(commit_to_point_to)
    
    console.print(f"Created new view [cyan]'{view_name}'[/cyan] pointing to commit [cyan]{commit_to_point_to[:12]}[/cyan].")
    console.print(f"To make it active, run: [bold]datagit activate {view_name}[/bold]")