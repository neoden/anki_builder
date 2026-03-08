"""HTML templates for Anki card backs."""

from .database import VocabularyEntry


def render_card_back(entry: VocabularyEntry) -> str:
    """Render HTML for the back of an Anki card.

    Args:
        entry: Vocabulary entry with all fields

    Returns:
        HTML string for card back
    """
    parts = []

    # Translation (always present)
    parts.append(f'<div class="translation">{entry.russian}</div>')

    # Word type
    if entry.word_type:
        parts.append(f'<div class="type">{entry.word_type}</div>')

    # Declension/forms (skip if invariable)
    if entry.declension and entry.declension.lower() not in ("invariable", "неизм.", "-"):
        parts.append(f'<div class="section"><span class="label">Формы:</span> {entry.declension}</div>')

    # Etymology
    if entry.etymology:
        parts.append(f'<div class="section"><span class="label">Этимология:</span> {entry.etymology}</div>')

    # Examples
    if entry.examples:
        examples_html = entry.examples.replace(" / ", "</p><p>")
        parts.append(f'<div class="examples"><span class="label">Примеры:</span><p>{examples_html}</p></div>')

    return "\n".join(parts)


# CSS for Anki card template (to be added manually in Anki)
ANKI_CSS = """\
.card {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 18px;
  text-align: center;
  color: #e8e8e8;
  background: #1a1a1a;
  padding: 20px;
  line-height: 1.5;
}

.translation {
  font-size: 28px;
  font-weight: bold;
  color: #4fc3f7;
  margin-bottom: 8px;
}

.type {
  display: inline-block;
  background: #333;
  color: #aaa;
  font-size: 13px;
  padding: 3px 10px;
  border-radius: 12px;
  margin-bottom: 16px;
}

.section {
  text-align: left;
  margin: 12px 0;
  padding: 10px 14px;
  background: #252525;
  border-radius: 8px;
  font-size: 16px;
}

.label {
  color: #888;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 4px;
}

.examples {
  text-align: left;
  margin: 12px 0;
  padding: 10px 14px;
  background: #1e3a2f;
  border-radius: 8px;
  font-size: 16px;
}

.examples p {
  margin: 6px 0;
}
"""
