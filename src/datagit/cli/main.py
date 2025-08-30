# src/datagit/cli/main.py
import typer
from datagit.cli import init, add  # import your subcommands here

app = typer.Typer(help="DataGit - Git-like version control for datasets")

# Register each command from other files
app.add_typer(init.app, name="")  # "" means top-level `datagit init`
app.add_typer(add.app, name="")   # top-level `datagit add`


def main():
    app()
