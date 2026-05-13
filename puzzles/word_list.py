"""Shared word list loader — loaded once per Streamlit session."""
from pathlib import Path

_WORDS_PATH = Path(__file__).parent.parent / "assets" / "words.txt"
_word_set: set | None = None


def get_word_set() -> set:
    global _word_set
    if _word_set is None:
        with open(_WORDS_PATH, encoding="utf-8") as f:
            _word_set = set(f.read().splitlines())
    return _word_set
