# # src/datagit/cli/commit.py
# import typer
# from pathlib import Path
# import json
# from datetime import datetime
# from rich.console import Console
# from datagit.storage import file as storage
# from datagit.storage import repo

# console = Console()
# app = typer.Typer()

# @app.command("commit")
# def commit_command(
#     message: str = typer.Option(..., "-m", "--message", help="Commit message")
# ):
#     """
#     Commit staged changes in the DataGit repository.
#     """
#     repo_path = repo.find_repo()
#     if not repo_path:
#         console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
#         raise typer.Exit(1)

#     metadata_path = repo_path / "metadata.json"
#     commits_dir = repo_path / "commits"

#     # Load index (staged changes)
#     index = storage.load_index(repo_path)
#     if not index:
#         console.print("[yellow]Nothing staged. Use 'datagit add <file>' first.[/yellow]")
#         raise typer.Exit(1)

#     # Load metadata
#     if metadata_path.exists():
#         metadata = json.loads(metadata_path.read_text())
#     else:
#         metadata = {"HEAD": None, "branch": "main", "commits": []}

#     commits_dir.mkdir(exist_ok=True)

#     # --- Check if changes exist compared to last commit ---
#     if metadata["HEAD"]:
#         head_commit_file = commits_dir / f"{metadata['HEAD']}.json"
#         if head_commit_file.exists():
#             head_commit = json.loads(head_commit_file.read_text())
#             last_snapshot = head_commit.get("files", {})

#             if last_snapshot == index:
#                 console.print("[green]Nothing to commit, working tree clean.[/green]")
#                 return

#     # Generate commit ID
#     commit_id = str(len(metadata["commits"]) + 1).zfill(4)  # e.g., "0001"

#     commit_data = {
#         "id": commit_id,
#         "message": message,
#         "files": index.copy(),  # snapshot of staged files
#         "parent": metadata["HEAD"],
#         "timestamp": datetime.utcnow().isoformat() + "Z",
#     }

#     # Save commit file
#     commit_file = commits_dir / f"{commit_id}.json"
#     commit_file.write_text(json.dumps(commit_data, indent=2))

#     # Update metadata
#     metadata["HEAD"] = commit_id
#     metadata["commits"].append(commit_id)
#     metadata_path.write_text(json.dumps(metadata, indent=2))

#     # Clear staging (index.json)
#     storage.save_index(repo_path, {})

#     console.print(f"[green]Committed as {commit_id}: {message}[/green]")
