import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from datetime import datetime

# Import our refactored storage modules
from datagit.storage import repo as repo_utils
from datagit.storage import repository

console = Console()
app = typer.Typer()

@app.command("log")
def log_command():
    """
    Displays the commit history of the current active view.
    """
    repo_path = repo_utils.find_repo()
    if not repo_path:
        console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
        raise typer.Exit(1)

    # 1. Get the current view and its head commit hash using the new repository logic
    current_view = repository.get_current_view_name(repo_path)
    current_commit_hash = repository.get_head_commit(repo_path)

    if not current_commit_hash:
        console.print(f"[yellow]No commits yet on view '{current_view}'.[/yellow]")
        return

    # 2. Prepare a table for rich display, showing the current view
    table = Table(title=f"DataGit Commit History (view: {current_view})")
    table.add_column("Commit", style="cyan", no_wrap=True)
    table.add_column("Message", style="green")
    table.add_column("Timestamp", style="magenta")

    # 3. Traverse the commit history from the view's HEAD backwards
    commit_count = 0
    while current_commit_hash:
        manifest = repository.get_manifest(repo_path, current_commit_hash)
        
        if not manifest:
            console.print(f"[bold red]Error: Corrupted history. Could not find commit '{current_commit_hash}'.[/bold red]")
            break

        message = manifest.get("message", "No commit message")
        timestamp_str = manifest.get("timestamp", "No timestamp")
        
        try:
            ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            formatted_ts = ts.strftime("%Y-%m-%d %H:%M:%S %Z")
        except (ValueError, AttributeError):
            formatted_ts = timestamp_str

        table.add_row(current_commit_hash, message, formatted_ts)
        commit_count += 1

        # Move to the parent commit for the next iteration
        current_commit_hash = manifest.get("parent")

    if commit_count > 0:
        console.print(table)

