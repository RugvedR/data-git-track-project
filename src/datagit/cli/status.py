# # src/datagit/cli/status.py

# import typer
# from pathlib import Path
# from rich.console import Console
# from datagit.storage import file as storage
# from datagit.storage import repo
# import json

# console = Console()
# app = typer.Typer()

# @app.command("status")
# def status_command():
#     """
#     Show the status of working directory, staging area, and last commit (HEAD).
#     """
#     repo_path = repo.find_repo()
#     if not repo_path:
#         console.print("[red]No DataGit repository found. Run 'datagit init' first.[/red]")
#         raise typer.Exit(1)

#     repo_root = repo_path.parent

#     # --- Load state ---
#     index = storage.load_index(repo_path)

#     metadata_path = repo_path / "metadata.json"
#     if metadata_path.exists():
#         meta = json.loads(metadata_path.read_text())
#     else:
#         meta = {"HEAD": None, "branch": "main", "commits": []}

#     head_commit = {}
#     if meta["HEAD"]:
#         commit_file = repo_path / "commits" / f"{meta['HEAD']}.json"
#         if commit_file.exists():
#             head_commit = json.loads(commit_file.read_text()).get("files", {})

#     working_files = storage.list_working_files(repo_root)

#     # --- Classify files ---
#     staged = []
#     modified = []
#     deleted = []
#     untracked = []

#     # Compare staged (index) with working dir
#     for rel_path, entry in index.items():
#         file_path = repo_root / rel_path
#         if not file_path.exists():
#             deleted.append(rel_path)
#             continue
#         current_hash = storage.hash_file(file_path)
#         if current_hash != entry["hash"]:
#             modified.append(rel_path)
#         else:
#             staged.append(rel_path)

#     # Detect untracked files (not in index or last commit)
#     tracked_files = set(index.keys()) | set(head_commit.keys())
#     for rel_path in working_files - tracked_files:
#         untracked.append(rel_path)

#     # --- Display results ---
#     if not staged and not modified and not deleted and not untracked:
#         console.print("[green]Nothing to commit, working tree clean.[/green]")
#         return

#     if staged:
#         console.print("[cyan]Changes to be committed:[/cyan]")
#         for f in staged:
#             console.print(f"  [green]{f}[/green]")

#     if modified:
#         console.print("[yellow]Changes not staged for commit:[/yellow]")
#         for f in modified:
#             console.print(f"  [yellow]{f}[/yellow]")

#     if deleted:
#         console.print("[red]Deleted (staged for removal):[/red]")
#         for f in deleted:
#             console.print(f"  [red]{f}[/red]")

#     if untracked:
#         console.print("[magenta]Untracked files:[/magenta]")
#         for f in untracked:
#             console.print(f"  [magenta]{f}[/magenta]")
