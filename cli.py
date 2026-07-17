"""SaleScout CLI.

Usage:
    python cli.py acme.com
    python cli.py acme.com --out briefs/
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from salescout.config import provider_name
from salescout.graph import run_scout
from salescout.tools import normalize_domain

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def run(
    domain: str = typer.Argument(..., help="Company domain, e.g. acme.com"),
    out: Path = typer.Option(Path("briefs"), help="Directory for saved briefs"),
) -> None:
    """Research DOMAIN and write an outreach brief + email drafts."""
    domain = normalize_domain(domain)
    console.print(
        Panel.fit(
            f"[bold]SaleScout[/bold] · target: [cyan]{domain}[/cyan] · "
            f"llm: [magenta]{provider_name()}[/magenta]"
        )
    )

    with console.status("Agents working — researcher → analyst → writer ..."):
        state = run_scout(domain)

    # agent trace
    table = Table(title="Agent trace", show_lines=False)
    table.add_column("agent", style="cyan")
    table.add_column("action", style="green")
    table.add_column("detail", style="dim")
    for event in state.get("trace", []):
        table.add_row(event["agent"], event["action"], str(event.get("detail", ""))[:80])
    console.print(table)

    if not state.get("brief_md"):
        console.print("[red]Run ended early — no brief produced.[/red]")
        for err in state.get("errors", []):
            console.print(f"[red]  · {err}[/red]")
        raise typer.Exit(code=1)

    out.mkdir(parents=True, exist_ok=True)
    brief_path = out / f"{domain.replace('.', '_')}.md"

    emails_md = "\n\n---\n\n## Email drafts\n\n" + "\n\n".join(
        f"**Subject:** {e.get('subject', '')}\n\n{e.get('body', '')}"
        for e in state.get("emails", [])
    )
    brief_path.write_text(state["brief_md"] + emails_md, encoding="utf-8")

    score = state.get("analysis", {}).get("fit_score", "n/a")
    console.print(f"\n[bold green]Done.[/bold green] fit_score={score} → {brief_path}")


if __name__ == "__main__":
    app()
