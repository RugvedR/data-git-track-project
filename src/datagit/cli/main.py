import typer
# Import the new and updated command modules
from datagit.cli import init, add, commit, log, status, activate, view

app = typer.Typer(
    help="DataGit - A novel, content-addressed version control system for datasets.",
    rich_markup_mode="markdown"
)

# Register each command module with the main application
app.add_typer(init.app, name="")
app.add_typer(add.app, name="")
app.add_typer(commit.app, name="")
app.add_typer(log.app, name="")
# The new `activate` command replaces the old `checkout`
app.add_typer(activate.app, name="")
# The new `view` command for managing branches
app.add_typer(view.app, name="")
app.add_typer(status.app, name="") # Status is not yet fully implemented for the new model

def main():
    """The main entry point for the DataGit CLI application."""
    app()
