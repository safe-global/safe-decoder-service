import typer

from app.commands.register_commands import register_commands

app = typer.Typer()

register_commands(app)

if __name__ == "__main__":
    app()
