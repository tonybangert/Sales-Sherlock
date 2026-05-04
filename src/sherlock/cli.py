"""Sherlock CLI — `sherlock brief ...`"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from sherlock import __version__
from sherlock.dossier import Dossier
from sherlock.render.html import render_html
from sherlock.render.markdown import render_markdown
from sherlock.researcher import generate_brief
from sherlock.sources.apollo import enrich_with_apollo
from sherlock.sources.linkedin import parse_linkedin_paste
from sherlock.sources.web import fetch_company_summary

load_dotenv()

app = typer.Typer(
    help="Sherlock — pre-call research briefs for revenue teams.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"sherlock v{__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Sherlock — pre-call research briefs for revenue teams."""


@app.command("brief")
def brief(
    linkedin_file: Optional[Path] = typer.Option(
        None,
        "--linkedin-file",
        "-l",
        help="Path to a .txt file containing the pasted LinkedIn profile text.",
    ),
    linkedin_stdin: bool = typer.Option(
        False,
        "--linkedin-stdin",
        help="Read the LinkedIn paste from stdin (use with `pbpaste | sherlock ...`).",
    ),
    company: Optional[str] = typer.Option(
        None,
        "--company",
        "-c",
        help="Company URL or domain (e.g. acme.com).",
    ),
    context: Optional[str] = typer.Option(
        None,
        "--context",
        "-x",
        help="Meeting context (e.g. '30-min discovery call about pricing').",
    ),
    output: Path = typer.Option(
        Path("brief.md"),
        "--out",
        "-o",
        help="Output file path. Format inferred from extension (.md or .html).",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Override the Claude model (default: claude-sonnet-4-6).",
    ),
    no_apollo: bool = typer.Option(
        False,
        "--no-apollo",
        help="Skip Apollo enrichment even if APOLLO_API_KEY is set.",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Walk through inputs interactively (good for first run).",
    ),
) -> None:
    """Generate a pre-call brief from a LinkedIn paste and a company URL."""

    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            Panel.fit(
                "[red]ANTHROPIC_API_KEY not set.[/red]\n\n"
                "Get a key at https://console.anthropic.com and set it:\n"
                "  export ANTHROPIC_API_KEY=sk-ant-...\n\n"
                "Or add it to a .env file in your working directory.",
                title="Missing API key",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # --- Resolve LinkedIn paste ---
    if linkedin_stdin:
        linkedin_text = sys.stdin.read()
    elif linkedin_file is not None:
        linkedin_text = linkedin_file.read_text(encoding="utf-8")
    elif interactive or (not linkedin_file and not linkedin_stdin):
        linkedin_text = _prompt_linkedin_paste()
    else:
        linkedin_text = ""

    if not linkedin_text.strip():
        console.print("[red]No LinkedIn paste provided.[/red]")
        raise typer.Exit(1)

    # --- Resolve company ---
    if not company:
        company = typer.prompt("Company URL or domain")

    # --- Resolve meeting context ---
    if not context:
        context = typer.prompt(
            "Meeting context (e.g. '30-min discovery call about pricing')",
            default="Discovery call",
        )

    # --- Run pipeline ---
    asyncio.run(
        _run(
            linkedin_text=linkedin_text,
            company=company,
            context=context,
            output=output,
            model=model,
            use_apollo=not no_apollo,
        )
    )


async def _run(
    linkedin_text: str,
    company: str,
    context: str,
    output: Path,
    model: Optional[str],
    use_apollo: bool,
) -> None:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        t1 = progress.add_task("Parsing LinkedIn paste...", total=None)
        linkedin = parse_linkedin_paste(linkedin_text)
        progress.update(t1, completed=1)

        t2 = progress.add_task(f"Fetching {company}...", total=None)
        company_summary = await fetch_company_summary(company)
        progress.update(t2, completed=1)

        apollo = None
        if use_apollo and os.getenv("APOLLO_API_KEY"):
            t3 = progress.add_task("Enriching with Apollo.io...", total=None)
            try:
                apollo = await enrich_with_apollo(
                    person_name=linkedin.name,
                    company_domain=company,
                )
            except Exception as exc:  # noqa: BLE001
                console.print(f"[yellow]Apollo enrichment failed: {exc}[/yellow]")
            progress.update(t3, completed=1)

        dossier = Dossier(
            linkedin=linkedin,
            company=company_summary,
            context=context,
            apollo=apollo,
        )

        t4 = progress.add_task("Generating brief sections (parallel)...", total=None)
        sections = await generate_brief(dossier, model=model)
        progress.update(t4, completed=1)

    if output.suffix.lower() == ".html":
        rendered = render_html(sections, dossier)
    else:
        rendered = render_markdown(sections, dossier)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")

    console.print(
        Panel.fit(
            f"[green]Brief saved to[/green] [bold]{output}[/bold]\n\n"
            "[dim]Open it, share it, post it.[/dim]",
            title="Done",
            border_style="green",
        )
    )


def _prompt_linkedin_paste() -> str:
    eof_hint = (
        "[bold]Ctrl+Z[/bold] then [bold]Enter[/bold]"
        if sys.platform == "win32"
        else "[bold]Ctrl+D[/bold]"
    )
    console.print(
        Panel.fit(
            "[bold]Paste the LinkedIn profile text below.[/bold]\n\n"
            "1. Open the LinkedIn profile in your browser\n"
            "2. Press [bold]Cmd/Ctrl + A[/bold] then [bold]Cmd/Ctrl + C[/bold]\n"
            f"3. Paste here, then press {eof_hint} to finish",
            title="LinkedIn paste",
            border_style="cyan",
        )
    )
    return sys.stdin.read()


if __name__ == "__main__":
    app()
