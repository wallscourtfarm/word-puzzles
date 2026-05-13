"""
Word Ladder puzzle generator.
BFS finds shortest path between two words, changing one letter per step.
"""
import json
import re
from collections import deque

import anthropic

from .word_list import get_word_set


def bfs_ladder(start: str, end: str, word_set: set) -> list[str] | None:
    """
    BFS from start to end (both lowercase, same length).
    Returns full path including start and end, or None if no path.
    Caps at 150 000 visited nodes to avoid runaway searches.
    """
    length = len(start)
    if len(end) != length:
        return None

    same_len = {w for w in word_set if len(w) == length}
    if start not in same_len or end not in same_len:
        return None

    queue: deque[tuple[str, list[str]]] = deque([(start, [start])])
    visited: set[str] = {start}

    while queue and len(visited) < 150_000:
        word, path = queue.popleft()
        for i in range(length):
            for ch in "abcdefghijklmnopqrstuvwxyz":
                if ch == word[i]:
                    continue
                neighbour = word[:i] + ch + word[i + 1:]
                if neighbour == end:
                    return path + [end]
                if neighbour in same_len and neighbour not in visited:
                    visited.add(neighbour)
                    queue.append((neighbour, path + [neighbour]))
    return None


def generate_word_ladder(topic: str, year_group: str, difficulty: str, api_key: str) -> dict:
    """
    Generate a Word Ladder puzzle.
    Returns dict: start, end, path (solution), word_length, num_steps, topic.
    """
    client = anthropic.Anthropic(api_key=api_key)
    year_num = year_group.replace("Y", "")
    word_set = get_word_set()

    step_hint = {"Easy": "3–4", "Medium": "5–6", "Hard": "7–8"}.get(difficulty, "4–6")

    prompt = f"""Suggest word pairs for a Word Ladder puzzle for Year {year_num} pupils (topic: "{topic}").

Rules:
- Both words in each pair must be the same length (4 or 5 letters preferred).
- Both words should be common English words familiar to 8-9 year olds.
- Ideally at least one word relates to "{topic}".
- A path of {step_hint} intermediate steps (not counting the start and end) should exist.

Return ONLY valid JSON, no markdown:
{{
  "pairs": [
    {{"start": "cold", "end": "warm"}},
    {{"start": "dark", "end": "glow"}},
    {{"start": "hard", "end": "soft"}},
    {{"start": "fire", "end": "wind"}}
  ]
}}

Provide at least 4 pairs so there are fallbacks."""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = re.sub(r"```[a-z]*", "", resp.content[0].text.strip()).strip("`")
    data = json.loads(raw)

    for pair in data.get("pairs", []):
        start = pair["start"].lower().strip()
        end = pair["end"].lower().strip()
        if start == end:
            continue
        path = bfs_ladder(start, end, word_set)
        if path and 2 <= len(path) - 2 <= 10:
            return {
                "start": start.upper(),
                "end": end.upper(),
                "path": [w.upper() for w in path],
                "word_length": len(start),
                "num_steps": len(path) - 2,
                "topic": topic,
            }

    raise ValueError(
        "Could not find a valid word ladder path for any suggested pair. "
        "Try a different topic or difficulty."
    )
