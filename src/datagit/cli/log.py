# # src/datagit/cli/log.py
# import typer
# from pathlib import Path
# import json
# from rich.console import Console
# from rich.table import Table
# from datetime import datetime
# from typing import Optional

# console = Console()
# app = typer.Typer()

# def load_metadata(repo_path: Path) -> dict:
#     """
#     Load repository metadata.json
#     """
#     metadata_path = repo_path / "metadata.json"
#     if not metadata_path.exists():
#         return {}
#     return json.loads(metadata_path.read_text())

# def load_commit(repo_path: Path, commit_id: str) -> Optional[dict]:
#     """
#     Load a specific commit file by commit_id.
#     """
#     commit_file = repo_path / "commits" / f"{commit_id}.json"
#     if not commit_file.exists():
#         return None
#     return json.loads(commit_file.read_text())

# @app.command("log")
# def log_command():
#     """
#     Show commit history.
#     """
#     repo_path = Path(".datagit")
#     if not repo_path.exists():
#         console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
#         raise typer.Exit(1)

#     metadata = load_metadata(repo_path)
#     commits = metadata.get("commits", [])

#     if not commits:
#         console.print("[yellow]No commits yet.[/yellow]")
#         return

#     # Display table of commits
#     table = Table(title="Commit History")
#     table.add_column("Commit ID", style="cyan", no_wrap=True)
#     table.add_column("Message", style="green")
#     table.add_column("Timestamp", style="magenta")

#     for commit_id in reversed(commits):  # newest first
#         commit_data = load_commit(repo_path, commit_id)
#         if not commit_data:
#             continue  # skip corrupted/missing

#         message = commit_data.get("message", "")
#         timestamp = commit_data.get("timestamp", "")

#         # Format timestamp safely
#         try:
#             ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
#             timestamp = ts.strftime("%Y-%m-%d %H:%M:%S")
#         except Exception:
#             pass

#         table.add_row(commit_id, message, timestamp)

#     console.print(table)
