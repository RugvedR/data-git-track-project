# src/datagit/cli/main.py
import typer
from datagit.cli import init  # import your subcommands here

app = typer.Typer(help="DataGit - Git-like version control for datasets")

# Register each command from other files
app.add_typer(init.app, name="")  # "" means top-level `datagit init`

def main():
    app()
