"""Export vocabulary to TSV for Anki import."""

import csv
from pathlib import Path
from .database import Database, VocabularyEntry
from .templates import render_card_back


def export_to_tsv(
    entries: list[VocabularyEntry],
    output_path: str | Path,
) -> int:
    """Export entries to TSV file for Anki import.

    Format: Greek<tab>HTML Back<tab>Tags (no header)

    Args:
        entries: List of vocabulary entries
        output_path: Path to output TSV file

    Returns:
        Number of entries exported
    """
    output_path = Path(output_path)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)

        for entry in entries:
            html_back = render_card_back(entry)
            writer.writerow([entry.greek, html_back, entry.tags])

    return len(entries)


def export_database(db: Database, output_path: str | Path) -> int:
    """Export entire database to TSV.

    Args:
        db: Database instance
        output_path: Path to output TSV file

    Returns:
        Number of entries exported
    """
    entries = db.get_all()
    return export_to_tsv(entries, output_path)


def import_tsv_to_database(
    tsv_path: str | Path,
    db: Database,
    on_progress: callable = None,
) -> dict:
    """Import existing TSV file into database.

    Expected format: Greek<tab>Russian<tab>WordType<tab>Declension<tab>Etymology<tab>Examples<tab>Tags
    (with header row)

    Args:
        tsv_path: Path to TSV file
        db: Database instance
        on_progress: Optional callback(current, total) for progress

    Returns:
        Dict with counts: {"inserted": N, "updated": N, "skipped": N}
    """
    tsv_path = Path(tsv_path)
    counts = {"inserted": 0, "updated": 0, "skipped": 0}

    with open(tsv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    total = len(rows)
    for i, row in enumerate(rows):
        entry = VocabularyEntry(
            greek=row.get("Greek", ""),
            russian=row.get("Russian", ""),
            word_type=row.get("WordType", ""),
            declension=row.get("Declension", ""),
            etymology=row.get("Etymology", ""),
            examples=row.get("Examples", ""),
            tags=row.get("Tags", ""),
        )

        if not entry.greek:
            continue

        action, _ = db.upsert(entry)
        counts[action] += 1

        if on_progress:
            on_progress(i + 1, total)

    return counts
