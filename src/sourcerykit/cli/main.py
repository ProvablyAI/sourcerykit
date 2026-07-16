import importlib.metadata

import typer

from sourcerykit.cli.config import config
from sourcerykit.cli.doctor import run_doctor
from sourcerykit.cli.endpoints import endpoints
from sourcerykit.cli.feedback import send_feedback
from sourcerykit.cli.init import config_provably
from sourcerykit.cli.trace import trace
from sourcerykit.cli.upgrade import run_upgrade
from sourcerykit.cli.utils import console
from sourcerykit.cli.utils import logout as logout_session

app = typer.Typer(no_args_is_help=True)
app.add_typer(endpoints, name="endpoints")
app.add_typer(config, name="config")
app.add_typer(trace, name="trace")


@app.command(help="interactive setup wizard (account, database, project)")
def init(
    register: bool = typer.Option(False, "--register", help="create a new account (requires --email and --password)"),
    email: str | None = typer.Option(None, "--email", help="account email"),
    password: str | None = typer.Option(None, "--password", help="account password"),
    postgres_url: str | None = typer.Option(None, "--postgres-url", help="full postgres:// URL"),
    project_name: str | None = typer.Option(None, "--project-name", help="project name"),
) -> None:
    config_provably(
        register=register,
        email=email,
        password=password,
        postgres_url=postgres_url,
        project_name=project_name,
    )


@app.command(help="validate configuration and connectivity")
def doctor(
    fix: bool = typer.Option(False, "--fix", help="auto-fix missing bootstrap IDs by running handshake"),
) -> None:
    run_doctor(fix=fix)


@app.command(help="send feedback")
def feedback(
    description: str | None = typer.Option(None, "--description", help="feedback description"),
    attach_file: str | None = typer.Option(None, "--attach-file", help="path to file to attach"),
) -> None:
    send_feedback(description=description, attach_file=attach_file)


@app.command(help="clear stored session (token)")
def logout() -> None:
    logout_session()
    console.print("🔒 Logged out. Run `sourcerykit init` to log in again.")


@app.command(help="print package version")
def version() -> None:
    v = importlib.metadata.version("sourcerykit")
    console.print(f"v{v}")


@app.command(help="upgrade package and run database migrations")
def upgrade() -> None:
    run_upgrade()


if __name__ == "__main__":
    app()
