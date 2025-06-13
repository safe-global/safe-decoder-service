import typer


def error(message: str):
    """
    Print styled error message

    param message:
    """
    typer.secho(message, fg=typer.colors.RED)


def success(message: str):
    """
    Print styled success message

    param message:
    """
    typer.secho(message, fg=typer.colors.GREEN)


def print_command_title(title: str):
    """
    Print command title

    param title:
    """
    typer.secho("=" * 50, fg=typer.colors.CYAN)
    typer.secho(title, fg=typer.colors.CYAN, bold=True)
    typer.secho("=" * 50, fg=typer.colors.CYAN)
