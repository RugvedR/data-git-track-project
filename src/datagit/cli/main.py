# src/datagit/cli/main.py
import typer
from datagit.cli import init, add, commit, log, status

app = typer.Typer(help="DataGit - Git-like version control for datasets")

# Register each command from other files
app.add_typer(init.app, name="")   # top-level `datagit init`
app.add_typer(add.app, name="")    # top-level `datagit add`
app.add_typer(commit.app, name="") # top-level `datagit commit`
app.add_typer(log.app, name="")    # top-level `datagit log`
# app.add_typer(status.app, name="") # top-level `datagit status`

def main():
    app()
