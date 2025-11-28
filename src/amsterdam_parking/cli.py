"""Command-line interface using Click."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from amsterdam_parking import __version__
from amsterdam_parking.bot import ParkingBot
from amsterdam_parking.config import AppConfig
from amsterdam_parking.session_calculator import SessionCalculator

console = Console()


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="amsterdam-parking")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Amsterdam Parking Automation - Book parking sessions optimally."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("time_range")
@click.option(
    "--tomorrow",
    is_flag=True,
    help="Book for tomorrow instead of today",
)
@click.option(
    "--session",
    type=int,
    metavar="MINUTES",
    help="Session duration in minutes (default: from config)",
)
@click.option(
    "--max-break",
    type=int,
    metavar="MINUTES",
    help="Maximum break between sessions (default: from config)",
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    default=Path("config.json"),
    help="Configuration file path",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Calculate sessions without booking",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
def book(
    time_range: str,
    tomorrow: bool,
    session: int | None,
    max_break: int | None,
    config: Path,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Book parking sessions for a time range.

    TIME_RANGE format: HH:MM-HH:MM (e.g., "13:00-14:00")

    Examples:

        \b
        # Book parking today from 13:00 to 14:00
        $ amsterdam-parking book "13:00-14:00"

        \b
        # Book for tomorrow with custom session duration
        $ amsterdam-parking book "09:00-17:00" --tomorrow --session 15

        \b
        # Calculate sessions without booking
        $ amsterdam-parking book "13:00-14:00" --dry-run
    """
    try:
        # Load configuration
        if not config.exists():
            app_config = AppConfig.create_default(config)
        else:
            app_config = AppConfig.from_json(config)

        if verbose:
            app_config.log_level = "DEBUG"

        # Override config with CLI options
        session_duration = session or app_config.session_duration_minutes
        max_break_duration = max_break or app_config.max_break_minutes

        # Calculate target date
        target_date = datetime.now() + timedelta(days=1) if tomorrow else None

        # Calculate sessions
        calculator = SessionCalculator(session_duration, max_break_duration)
        start_time, end_time = calculator.parse_time_range(time_range, target_date)
        sessions = calculator.calculate_sessions(start_time, end_time)

        if dry_run:
            # Display calculated sessions
            console.print(f"\n[bold]Calculated {len(sessions)} sessions:[/bold]\n")
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=3)
            table.add_column("Session Time")
            table.add_column("Duration", justify="right")

            for i, sess in enumerate(sessions, 1):
                table.add_row(str(i), str(sess), f"{sess.duration_minutes} min")

            console.print(table)
            return

        # Book sessions
        bot = ParkingBot(app_config)
        date_str = "tomorrow" if tomorrow else "today"
        console.print(f"\n[bold]Booking {len(sessions)} sessions for {date_str}...[/bold]\n")

        result = bot.book_sessions(sessions, tomorrow)

        # Display results
        if result:
            console.print(f"\n[bold green]✓ Success:[/bold green] {result.successful_sessions}/{result.total_sessions} sessions booked")
            if result.failed_sessions > 0:
                console.print(f"[bold yellow]⚠ Warning:[/bold yellow] {result.failed_sessions} sessions failed")
                sys.exit(2)
        else:
            console.print("[bold red]✗ Error:[/bold red] Booking failed")
            sys.exit(1)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("time_range")
@click.option(
    "--session",
    type=int,
    default=10,
    help="Session duration in minutes",
)
@click.option(
    "--max-break",
    type=int,
    default=5,
    help="Maximum break between sessions",
)
def calculate(time_range: str, session: int, max_break: int) -> None:
    """Calculate optimal session splits without configuration.

    TIME_RANGE format: HH:MM-HH:MM

    Example:

        \b
        $ amsterdam-parking calculate "13:00-16:00" --session 15 --max-break 3
    """
    try:
        calculator = SessionCalculator(session, max_break)
        start_time, end_time = calculator.parse_time_range(time_range)
        sessions = calculator.calculate_sessions(start_time, end_time)

        console.print(f"\n[bold]Calculated {len(sessions)} sessions:[/bold]\n")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("Session Time")
        table.add_column("Duration", justify="right")

        for i, sess in enumerate(sessions, 1):
            table.add_row(str(i), str(sess), f"{sess.duration_minutes} min")

        console.print(table)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--config",
    type=click.Path(path_type=Path),
    default=Path("config.json"),
    help="Configuration file path",
)
def init(config: Path) -> None:
    """Initialize configuration file with defaults."""
    try:
        if config.exists():
            if not click.confirm(f"{config} already exists. Overwrite?"):
                return

        AppConfig.create_default(config)
        console.print(f"[green]✓[/green] Created configuration file: {config}")
        console.print("\n[yellow]⚠[/yellow] Please update your credentials in the config file:")
        console.print(f"  $ nano {config}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
