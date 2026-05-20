#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="run-allure",
    help="Run pytest suites and generate Allure trend reports.",
    rich_markup_mode="rich",
    no_args_is_help=False,
)

console = Console()
err_console = Console(stderr=True)

# ── Defaults ──────────────────────────────────────────────────────────────────
RESULTS_DIR_DEFAULT = "allure-results"
REPORT_DIR_DEFAULT = "allure-report"
CONFIG_FILE_DEFAULT = "allurerc.yml"
HISTORY_FILE_DEFAULT = ".allure/allure-history.jsonl"
HISTORY_LIMIT_DEFAULT = 2
RUNS_DEFAULT = 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(command: str, description: str, *, capture: bool = False) -> str:
    """Execute a shell command, streaming output unless *capture* is True."""
    console.print(f"\n  [bold cyan]▶[/bold cyan] [dim]{description}[/dim]")
    console.print(f"  [dim]$ {command}[/dim]")
    result = subprocess.run(
        command,
        shell=True,
        capture_output=capture,
        text=True,
    )
    if result.returncode != 0:
        err_console.print(
            Panel(
                f"[bold red]Command failed[/bold red] (exit {result.returncode})\n[dim]$ {command}[/dim]",
                border_style="red",
                title="Error",
            )
        )
        raise typer.Exit(result.returncode)
    return result.stdout.strip() if capture else ""


def _remove(path: str) -> None:
    p = Path(path)
    if p.is_dir():
        shutil.rmtree(p)
        console.print(f"  [yellow]removed[/yellow]  {path}/")
    elif p.exists():
        p.unlink()
        console.print(f"  [yellow]removed[/yellow]  {path}")


def _clean(results_dir: str, report_dir: str, history_file: str) -> None:
    console.print(Rule("[bold]Cleaning environment[/bold]", style="dim"))
    _remove(results_dir)
    _remove(report_dir)
    _remove(history_file)
    Path(history_file).parent.mkdir(parents=True, exist_ok=True)
    Path(history_file).write_text("")
    console.print(f"  [green]created[/green]   {history_file} [dim](empty)[/dim]")


def _allure_version() -> str:
    return _run("allure --version", "Checking Allure CLI version", capture=True)


def _summary_table(
    runs: int,
    results_dir: str,
    report_dir: str,
    config_file: str,
    history_file: str,
    history_limit: int,
    pytest_args: str,
    open_report: bool,
) -> Table:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim", justify="right")
    table.add_column(style="bold white")

    rows = [
        ("runs", str(runs)),
        ("results dir", results_dir),
        ("report dir", report_dir),
        ("config file", config_file),
        ("history file", history_file),
        ("history limit", str(history_limit)),
        ("pytest extra args", pytest_args or "[dim]none[/dim]"),
        ("open report", "[green]yes[/green]" if open_report else "[yellow]no[/yellow]"),
    ]
    for label, value in rows:
        table.add_row(label, value)
    return table


# ── CLI command ───────────────────────────────────────────────────────────────

@app.command()
def run(
    runs: Annotated[
        int,
        typer.Option("--runs", "-n", help="Number of pytest+generate cycles to execute.", min=1),
    ] = RUNS_DEFAULT,
    results_dir: Annotated[
        str,
        typer.Option("--results-dir", "-r", help="Directory for raw Allure results."),
    ] = RESULTS_DIR_DEFAULT,
    report_dir: Annotated[
        str,
        typer.Option("--report-dir", "-o", help="Directory for the generated Allure report."),
    ] = REPORT_DIR_DEFAULT,
    config_file: Annotated[
        str,
        typer.Option("--config", "-c", help="Allure configuration file."),
    ] = CONFIG_FILE_DEFAULT,
    history_file: Annotated[
        str,
        typer.Option("--history-file", help="Path to the Allure history JSONL ledger."),
    ] = HISTORY_FILE_DEFAULT,
    history_limit: Annotated[
        int,
        typer.Option("--history-limit", help="Number of historical runs to keep.", min=1),
    ] = HISTORY_LIMIT_DEFAULT,
    pytest_args: Annotated[
        str,
        typer.Option("--pytest-args", help='Extra arguments forwarded to pytest, e.g. "-k smoke".'),
    ] = "",
    open_report: Annotated[
        bool,
        typer.Option("--open/--no-open", help="Open the Allure report in the browser when done."),
    ] = True,
    clean: Annotated[
        bool,
        typer.Option("--clean/--no-clean", help="Wipe existing results/report/history before starting."),
    ] = True,
) -> None:
    """Run [bold cyan]pytest[/bold cyan] + [bold cyan]allure generate[/bold cyan] in a loop to build trend history."""

    # ── Header ────────────────────────────────────────────────────────────────
    console.print()
    console.print(
        Panel.fit(
            "[bold white]Allure Trend Runner[/bold white]",
            subtitle="[dim]petstore-api[/dim]",
            border_style="cyan",
        )
    )

    allure_ver = _allure_version()
    console.print(f"\n  [dim]allure[/dim] [green]{allure_ver}[/green]")

    console.print()
    console.print(Rule("[bold]Configuration[/bold]", style="dim"))
    console.print(_summary_table(
        runs, results_dir, report_dir, config_file, history_file, history_limit, pytest_args, open_report,
    ))

    # ── Clean ─────────────────────────────────────────────────────────────────
    if clean:
        console.print()
        _clean(results_dir, report_dir, history_file)

    # ── Run loop ──────────────────────────────────────────────────────────────
    console.print()
    for i in range(runs):
        label = f"Run [bold]{i + 1}[/bold] / {runs}"
        console.print(Rule(label, style="blue"))

        # Wipe stale artefacts before each cycle
        _remove(results_dir)
        _remove(report_dir)

        extra = f" {pytest_args}" if pytest_args else ""
        _run(
            f"uv run pytest -q --alluredir={results_dir}{extra}",
            f"pytest (run {i + 1})",
        )
        _run(
            f"allure generate --config {config_file} --history-limit {history_limit}",
            f"allure generate (run {i + 1})",
        )

        console.print(f"  [green]✓[/green] cycle {i + 1}/{runs} complete")

    # ── Summary ───────────────────────────────────────────────────────────────
    console.print()
    console.print(
        Panel(
            Text.assemble(
                ("All ", "white"),
                (str(runs), "bold green"),
                (" run(s) completed successfully.\n\n", "white"),
                ("History ledger → ", "dim"),
                (history_file, "cyan"),
            ),
            title="[bold green]Done[/bold green]",
            border_style="green",
        )
    )

    # ── Open report ───────────────────────────────────────────────────────────
    if open_report:
        console.print()
        _run(f"allure open {report_dir}", "Opening Allure report in browser")


if __name__ == "__main__":
    app()
