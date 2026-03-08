"""SQLite database operations for vocabulary storage."""

import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass


@dataclass
class VocabularyEntry:
    greek: str
    russian: str
    word_type: str = ""
    declension: str = ""
    etymology: str = ""
    examples: str = ""
    tags: str = ""
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_complete(self) -> bool:
        """Check if entry has all enrichment data."""
        return bool(self.word_type and self.etymology and self.examples and self.tags)

    def can_be_enriched_from(self, other: "VocabularyEntry") -> bool:
        """Check if this entry can be enriched with data from another."""
        dominated = [
            (not self.word_type and other.word_type),
            (not self.declension and other.declension),
            (not self.etymology and other.etymology),
            (not self.examples and other.examples),
            (not self.tags and other.tags),
        ]
        return any(dominated)

    def merge_from(self, other: "VocabularyEntry") -> None:
        """Merge non-empty fields from another entry."""
        if not self.word_type and other.word_type:
            self.word_type = other.word_type
        if not self.declension and other.declension:
            self.declension = other.declension
        if not self.etymology and other.etymology:
            self.etymology = other.etymology
        if not self.examples and other.examples:
            self.examples = other.examples
        if not self.tags and other.tags:
            self.tags = other.tags


class Database:
    def __init__(self, db_path: str | Path = "vocabulary.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                greek TEXT UNIQUE NOT NULL,
                russian TEXT NOT NULL,
                word_type TEXT DEFAULT '',
                declension TEXT DEFAULT '',
                etymology TEXT DEFAULT '',
                examples TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def find_by_greek(self, greek: str) -> VocabularyEntry | None:
        """Find entry by Greek word/phrase."""
        row = self.conn.execute(
            "SELECT * FROM vocabulary WHERE greek = ?", (greek,)
        ).fetchone()
        if row:
            return VocabularyEntry(
                id=row["id"],
                greek=row["greek"],
                russian=row["russian"],
                word_type=row["word_type"] or "",
                declension=row["declension"] or "",
                etymology=row["etymology"] or "",
                examples=row["examples"] or "",
                tags=row["tags"] or "",
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        return None

    def insert(self, entry: VocabularyEntry) -> int:
        """Insert new entry, return its ID."""
        cursor = self.conn.execute(
            """
            INSERT INTO vocabulary (greek, russian, word_type, declension, etymology, examples, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.greek,
                entry.russian,
                entry.word_type,
                entry.declension,
                entry.etymology,
                entry.examples,
                entry.tags,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update(self, entry: VocabularyEntry) -> None:
        """Update existing entry."""
        self.conn.execute(
            """
            UPDATE vocabulary
            SET russian = ?, word_type = ?, declension = ?, etymology = ?,
                examples = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
            WHERE greek = ?
            """,
            (
                entry.russian,
                entry.word_type,
                entry.declension,
                entry.etymology,
                entry.examples,
                entry.tags,
                entry.greek,
            ),
        )
        self.conn.commit()

    def upsert(self, entry: VocabularyEntry) -> tuple[str, VocabularyEntry]:
        """Insert or update entry with smart merging.

        Returns: (action, final_entry) where action is 'inserted', 'updated', or 'skipped'
        """
        existing = self.find_by_greek(entry.greek)

        if existing is None:
            entry_id = self.insert(entry)
            entry.id = entry_id
            return ("inserted", entry)

        if existing.is_complete():
            return ("skipped", existing)

        if existing.can_be_enriched_from(entry):
            existing.merge_from(entry)
            self.update(existing)
            return ("updated", existing)

        return ("skipped", existing)

    def get_all(self) -> list[VocabularyEntry]:
        """Get all entries."""
        rows = self.conn.execute("SELECT * FROM vocabulary ORDER BY greek").fetchall()
        return [
            VocabularyEntry(
                id=row["id"],
                greek=row["greek"],
                russian=row["russian"],
                word_type=row["word_type"] or "",
                declension=row["declension"] or "",
                etymology=row["etymology"] or "",
                examples=row["examples"] or "",
                tags=row["tags"] or "",
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def count(self) -> int:
        """Get total entry count."""
        return self.conn.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]

    def close(self) -> None:
        self.conn.close()
