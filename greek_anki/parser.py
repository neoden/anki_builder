"""Chat parser using Claude API to extract Greek-Russian word pairs."""

import json
from anthropic import Anthropic

PARSE_PROMPT = """\
Extract Greek vocabulary words with their Russian translations from this chat log.

The chat contains messages from a Greek teacher. Each learning entry has:
- A Greek word or phrase (may include article like Ο/Η/Το or pronoun like Εγώ)
- A Russian translation

Ignore:
- Timestamps (like 09:33)
- Names (like "Анна П.")
- "img" markers
- Any non-vocabulary content

Return a JSON array of objects with "greek" and "russian" fields.
Example output:
[
  {{"greek": "Εγώ συγκρίνω", "russian": "сравниваю"}},
  {{"greek": "Ο άγριος / η / το", "russian": "дикий"}}
]

Chat log:
{text}

Return ONLY the JSON array, no other text."""


def parse_chat(client: Anthropic, text: str, model: str = "claude-sonnet-4-20250514") -> list[dict]:
    """Parse chat text using Claude to extract Greek-Russian pairs.

    Args:
        client: Anthropic client
        text: Raw chat text (copy-paste from messenger)
        model: Claude model to use

    Returns:
        List of {"greek": str, "russian": str} dicts
    """
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "user", "content": PARSE_PROMPT.format(text=text)}
        ],
    )

    content = response.content[0].text.strip()

    # Handle potential markdown code blocks
    if "```" in content:
        # Extract content between ``` markers
        import re
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if match:
            content = match.group(1).strip()

    # Try to find JSON array if there's extra text
    if not content.startswith("["):
        start = content.find("[")
        end = content.rfind("]") + 1
        if start != -1 and end > start:
            content = content[start:end]

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}\nContent was:\n{content[:500]}")
