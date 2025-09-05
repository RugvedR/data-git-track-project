# src/datagit/cli/main.py
import typer
from datagit.cli import init, add, commit, log 

app = typer.Typer(help="DataGit - Git-like version control for datasets")

# Register each command from other files
app.add_typer(init.app, name="")  # "" means top-level `datagit init`
app.add_typer(add.app, name="")   # top-level `datagit add`
app.add_typer(commit.app, name="")
app.add_typer(log.app, name="")

def main():
    app()
