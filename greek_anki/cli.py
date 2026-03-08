"""CLI interface for Greek Anki tool."""

import os
import sys
from pathlib import Path

import click
import pyperclip
from anthropic import Anthropic
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from .database import Database, VocabularyEntry
from .parser import parse_chat
from .enricher import enrich_entry
from .exporter import export_to_tsv, export_database, import_tsv_to_database
from .templates import render_card_back, ANKI_CSS

console = Console()

DEFAULT_DB_PATH = Path.home() / ".greek-anki" / "vocabulary.db"
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def get_client() -> Anthropic:
    """Get Anthropic client from environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY environment variable not set[/red]")
        sys.exit(1)
    return Anthropic(api_key=api_key)


def ensure_db_dir(db_path: Path) -> None:
    """Ensure database directory exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)


@click.group()
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH),
              help="Path to SQLite database")
@click.pass_context
def main(ctx, db_path: str):
    """Greek Anki - Create vocabulary flashcards from chat."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = Path(db_path)


@main.command()
@click.option("--file", "-f", "input_file", type=click.Path(exists=True),
              help="Read from file instead of clipboard")
@click.option("--stdin", "use_stdin", is_flag=True,
              help="Read from stdin instead of clipboard")
@click.option("--output", "-o", type=click.Path(), default="new-cards.tsv",
              help="Output TSV file path")
@click.option("--model", default=DEFAULT_MODEL, help="Claude model to use")
@click.option("--yes", "-y", "auto_confirm", is_flag=True,
              help="Auto-confirm saving without prompt")
@click.pass_context
def process(ctx, input_file: str | None, use_stdin: bool, output: str, model: str, auto_confirm: bool):
    """Process chat and create Anki cards."""
    db_path = ctx.obj["db_path"]
    ensure_db_dir(db_path)

    # Get input text
    if use_stdin:
        text = sys.stdin.read()
        console.print("[dim]Reading from stdin...[/dim]")
    elif input_file:
        text = Path(input_file).read_text(encoding="utf-8")
        console.print(f"[dim]Reading from {input_file}...[/dim]")
    else:
        try:
            text = pyperclip.paste()
            console.print("[dim]Reading from clipboard...[/dim]")
        except Exception as e:
            console.print(f"[red]Error reading clipboard: {e}[/red]")
            console.print("[yellow]Try using --file or --stdin instead[/yellow]")
            sys.exit(1)

    if not text.strip():
        console.print("[red]Error: No text to process[/red]")
        sys.exit(1)

    client = get_client()
    db = Database(db_path)

    # Step 1: Parse chat
    console.print("\n[bold]Step 1: Parsing chat...[/bold]")
    with console.status("Extracting words..."):
        try:
            parsed = parse_chat(client, text, model)
        except Exception as e:
            console.print(f"[red]Error parsing chat: {e}[/red]")
            sys.exit(1)

    if not parsed:
        console.print("[yellow]No words found in the text[/yellow]")
        sys.exit(0)

    # Show parsed words
    table = Table(title=f"Found {len(parsed)} words")
    table.add_column("#", style="dim")
    table.add_column("Greek", style="cyan")
    table.add_column("Russian", style="green")
    table.add_column("Status", style="yellow")

    entries_to_process = []
    for i, item in enumerate(parsed, 1):
        greek = item["greek"]
        russian = item["russian"]

        existing = db.find_by_greek(greek)
        if existing and existing.is_complete():
            status = "exists (complete)"
        elif existing:
            status = "exists (incomplete)"
            entries_to_process.append(VocabularyEntry(greek=greek, russian=russian))
        else:
            status = "new"
            entries_to_process.append(VocabularyEntry(greek=greek, russian=russian))

        table.add_row(str(i), greek, russian, status)

    console.print(table)

    if not entries_to_process:
        console.print("\n[green]All words already in database with complete data.[/green]")
        sys.exit(0)

    # Step 2: Enrich
    console.print(f"\n[bold]Step 2: Enriching {len(entries_to_process)} words...[/bold]")

    enriched = []
    for i, entry in enumerate(entries_to_process, 1):
        console.print(f"\n[dim]({i}/{len(entries_to_process)})[/dim] [cyan]{entry.greek}[/cyan]")
        with console.status("Fetching data..."):
            try:
                enrich_entry(client, entry, model)
                enriched.append(entry)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                continue

        # Show enriched entry
        console.print(Panel(
            f"[green]{entry.russian}[/green]\n"
            f"[dim]Type:[/dim] {entry.word_type}\n"
            f"[dim]Forms:[/dim] {entry.declension}\n"
            f"[dim]Etymology:[/dim] {entry.etymology}\n"
            f"[dim]Examples:[/dim] {entry.examples}\n"
            f"[dim]Tags:[/dim] {entry.tags}",
            title=entry.greek,
            border_style="blue"
        ))

    if not enriched:
        console.print("[red]No entries were enriched successfully[/red]")
        sys.exit(1)

    # Step 3: Confirm and save
    console.print(f"\n[bold]Step 3: Save {len(enriched)} entries?[/bold]")

    if not auto_confirm and not Confirm.ask("Save to database and export TSV?"):
        console.print("[yellow]Cancelled[/yellow]")
        sys.exit(0)

    # Save to database
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    for entry in enriched:
        action, _ = db.upsert(entry)
        counts[action] += 1

    console.print(f"[green]Database: {counts['inserted']} inserted, {counts['updated']} updated, {counts['skipped']} skipped[/green]")

    # Export to TSV
    export_to_tsv(enriched, output)
    console.print(f"[green]Exported to {output}[/green]")

    # Print TSV to stdout for easy copy
    console.print("\n[bold]TSV for import:[/bold]")
    print(Path(output).read_text())

    db.close()


@main.command("import")
@click.argument("tsv_file", type=click.Path(exists=True))
@click.pass_context
def import_cmd(ctx, tsv_file: str):
    """Import existing TSV file into database."""
    db_path = ctx.obj["db_path"]
    ensure_db_dir(db_path)

    db = Database(db_path)

    console.print(f"[dim]Importing from {tsv_file}...[/dim]")

    with console.status("Importing...") as status:
        def progress(current, total):
            status.update(f"Importing... {current}/{total}")

        counts = import_tsv_to_database(tsv_file, db, on_progress=progress)

    console.print(f"[green]Done: {counts['inserted']} inserted, {counts['updated']} updated, {counts['skipped']} skipped[/green]")
    console.print(f"[dim]Total entries in database: {db.count()}[/dim]")

    db.close()


@main.command()
@click.argument("output", type=click.Path(), default="vocabulary-export.tsv")
@click.pass_context
def export(ctx, output: str):
    """Export database to TSV for Anki import."""
    db_path = ctx.obj["db_path"]

    if not db_path.exists():
        console.print(f"[red]Database not found: {db_path}[/red]")
        sys.exit(1)

    db = Database(db_path)

    count = export_database(db, output)
    console.print(f"[green]Exported {count} entries to {output}[/green]")

    db.close()


@main.command()
def css():
    """Print CSS for Anki card template."""
    print(ANKI_CSS)


@main.command()
@click.pass_context
def stats(ctx):
    """Show database statistics."""
    db_path = ctx.obj["db_path"]

    if not db_path.exists():
        console.print(f"[yellow]Database not found: {db_path}[/yellow]")
        sys.exit(0)

    db = Database(db_path)

    entries = db.get_all()
    complete = sum(1 for e in entries if e.is_complete())

    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print(f"[bold]Total entries:[/bold] {len(entries)}")
    console.print(f"[bold]Complete:[/bold] {complete}")
    console.print(f"[bold]Incomplete:[/bold] {len(entries) - complete}")

    db.close()


if __name__ == "__main__":
    main()
