"""Enrichment of vocabulary entries using Claude API."""

import json
from anthropic import Anthropic
from .database import VocabularyEntry

ENRICH_PROMPT = """\
You are a Greek language expert helping create Anki flashcards for Russian speakers learning Modern Greek.

For this Greek word/phrase, provide enrichment data:

Greek: {greek}
Russian translation: {russian}

Return a JSON object with these fields:
{{
  "word_type": "noun|verb|adjective|adverb|phrase|expression",
  "declension": "grammatical forms - for nouns: article + genitive; for verbs: present, future, past; for adjectives: ος/η/ο forms; 'invariable' if not applicable",
  "etymology": "Greek roots, prefixes, suffixes with meanings. Connect to related words. Be concise.",
  "examples": "2 example sentences in Greek with Russian translations in parentheses, separated by ' / '",
  "tags": "2-4 space-separated tags for categorization (e.g., 'noun food restaurant' or 'verb actions movement')"
}}

Guidelines:
- For verbs starting with "Εγώ", include the verb forms without the pronoun in declension
- Etymology should show word formation: roots + affixes → meaning
- Examples should be practical, everyday sentences
- Tags should include word_type and 1-3 thematic tags

Return ONLY the JSON object, no other text."""


def enrich_entry(
    client: Anthropic,
    entry: VocabularyEntry,
    model: str = "claude-sonnet-4-20250514",
) -> VocabularyEntry:
    """Enrich a vocabulary entry with additional data from Claude.

    Args:
        client: Anthropic client
        entry: Entry with at least greek and russian filled
        model: Claude model to use

    Returns:
        Enriched entry (same object, modified in place)
    """
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": ENRICH_PROMPT.format(greek=entry.greek, russian=entry.russian),
            }
        ],
    )

    content = response.content[0].text.strip()

    # Handle potential markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    data = json.loads(content)

    entry.word_type = data.get("word_type", "")
    entry.declension = data.get("declension", "")
    entry.etymology = data.get("etymology", "")
    entry.examples = data.get("examples", "")
    entry.tags = data.get("tags", "")

    return entry


def enrich_entries(
    client: Anthropic,
    entries: list[VocabularyEntry],
    model: str = "claude-sonnet-4-20250514",
    on_progress: callable = None,
) -> list[VocabularyEntry]:
    """Enrich multiple entries.

    Args:
        client: Anthropic client
        entries: List of entries to enrich
        model: Claude model to use
        on_progress: Optional callback(index, total, entry) for progress updates

    Returns:
        List of enriched entries
    """
    for i, entry in enumerate(entries):
        enrich_entry(client, entry, model)
        if on_progress:
            on_progress(i + 1, len(entries), entry)

    return entries
