import importlib.metadata

import typer

from sourcerykit.cli.config import config
from sourcerykit.cli.doctor import run_doctor
from sourcerykit.cli.endpoints import endpoints
from sourcerykit.cli.feedback import send_feedback
from sourcerykit.cli.init import config_provably
from sourcerykit.cli.utils import console
from sourcerykit.cli.utils import logout as logout_session

app = typer.Typer(no_args_is_help=True)
app.add_typer(endpoints, name="endpoints")
app.add_typer(config, name="config")


@app.command(help="interactive setup wizard (account, database, project)")
def init() -> None:
    config_provably()


@app.command(help="validate configuration and connectivity")
def doctor(
    fix: bool = typer.Option(False, "--fix", help="auto-fix missing bootstrap IDs by running handshake"),
) -> None:
    run_doctor(fix=fix)


@app.command(help="send feedback")
def feedback() -> None:
    send_feedback()


@app.command(help="clear stored session (token)")
def logout() -> None:
    logout_session()
    console.print("🔒 Logged out. Run `sourcerykit init` to log in again.")


@app.command(help="print package version")
def version() -> None:
    v = importlib.metadata.version("sourcerykit")
    console.print(f"v{v}")


if __name__ == "__main__":
    app()
