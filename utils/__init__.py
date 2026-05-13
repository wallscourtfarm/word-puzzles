"""
Claude API helpers for topic-to-words generation and clue generation.
Falls back gracefully if the API key is absent (returns empty list).
"""
import json
import re


def get_words_from_topic(topic: str, year_group: str, puzzle_type: str, n: int = 16, api_key: str = "") -> tuple[list[str], str]:
    """
    Ask Claude to generate n vocabulary words for a given topic.
    Returns (words, display_title).
    """
    if not api_key:
        return [], topic

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    year_num = year_group.replace("Y", "")
    prompt = f"""Generate {n} vocabulary words for a Year {year_num} primary school class on the topic of "{topic}".
These words will be used in a {puzzle_type} puzzle.

Rules:
- Each word must be a single word (no spaces, no hyphens).
- Between 4 and 12 letters long.
- Appropriate for the age group (8-9 years old for Y4).
- Directly relevant to the curriculum topic.
- Mix of shorter and longer words.
- British English spelling.

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{{"words": ["word1", "word2", ...], "display_title": "Short human-readable topic name"}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r"```[a-z]*", "", raw).strip().strip("`")

    data = json.loads(raw)
    words = [w.strip().upper() for w in data.get("words", []) if w.strip()]
    display = data.get("display_title", topic)
    return words, display


def get_definitions_for_words(words: list[str], topic: str, year_group: str, api_key: str = "") -> dict[str, str]:
    """
    Return a dict of {WORD: "short child-friendly definition"}.
    Used for definition-match and crossword clues.
    """
    if not api_key or not words:
        return {}

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    year_num = year_group.replace("Y", "")
    word_list = ", ".join(words)

    prompt = f"""Write a short, child-friendly definition for each of the following words.
Context: Year {year_num} primary school, topic of {topic}.
Words: {word_list}

Each definition should:
- Be one sentence, 8-15 words.
- Be clear enough for a {int(year_num) + 4}-year-old.
- Not use the word itself in the definition.
- British English.

Return ONLY valid JSON (no markdown):
{{"WORD1": "definition one", "WORD2": "definition two", ...}}

Use the words exactly as given (uppercase)."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"```[a-z]*", "", raw).strip().strip("`")
    return json.loads(raw)
