"""
WFA Word Puzzle Generator — Streamlit app
Puzzle types: Word Search · Nine Letters · Word Ladder · Word Scramble · Cloze Passage
"""
import sys
import os
import re
import base64
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

from puzzles.word_search import generate_word_search
from puzzles.nine_letters import generate_nine_letters
from puzzles.word_ladder import generate_word_ladder
from puzzles.word_scramble import generate_word_scramble
from puzzles.cloze_passage import generate_cloze

from pdf_output.word_search_pdf import render_word_search_pdf
from pdf_output.nine_letters_pdf import render_nine_letters_pdf
from pdf_output.word_ladder_pdf import render_word_ladder_pdf
from pdf_output.word_scramble_pdf import render_word_scramble_pdf
from pdf_output.cloze_passage_pdf import render_cloze_pdf

from utils import get_words_from_topic, get_clf_words

st.set_page_config(
    page_title="WFA Word Puzzle Generator",
    page_icon="🔤",
    layout="centered",
)

LOGO_PATH = Path("assets/wfa_logo.webp")
YEAR_COLOURS = {
    "Y1": "#e57d24", "Y2": "#2bae62", "Y3": "#c0157b",
    "Y4": "#1798d3", "Y5": "#e57d24", "Y6": "#2bae62",
}

st.markdown("""
<style>
div[data-testid="stMainBlockContainer"] { max-width: 860px; margin: 0 auto; }
div[data-testid="stButton"] button {
    background-color: #1798d3 !important; border-color: #1798d3 !important; color: #ffffff !important;
}
div[data-testid="stButton"] button:hover {
    background-color: #1280b8 !important; border-color: #1280b8 !important;
}
div[data-testid="stDownloadButton"] > button {
    background: #ffffff !important; border: 1.5px solid #1798d3 !important; color: #1798d3 !important;
}
div[data-testid="stDownloadButton"] > button:hover { background: #f0f8ff !important; }
[data-baseweb="select"] > div { border-color: #cccccc !important; }
[data-baseweb="select"] > div:focus-within {
    border-color: #1798d3 !important; box-shadow: 0 0 0 3px #1798d333 !important;
}
[data-baseweb="input"] > div, [data-baseweb="textarea"] > div { border-color: #cccccc !important; }
[data-baseweb="input"] > div:focus-within, [data-baseweb="textarea"] > div:focus-within {
    border-color: #1798d3 !important; box-shadow: 0 0 0 3px #1798d333 !important;
}
[data-baseweb="radio"] [data-checked="true"] > div,
[data-baseweb="checkbox"] [data-checked="true"] > div {
    background-color: #1798d3 !important; border-color: #1798d3 !important;
}
div[data-testid="stProgressBar"] > div > div { background-color: #1798d3 !important; }
button[data-baseweb="tab"][aria-selected="true"] {
    border-bottom-color: #1798d3 !important; color: #1798d3 !important;
}
</style>
""", unsafe_allow_html=True)

if LOGO_PATH.exists():
    logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:18px;margin-bottom:6px;">'
        f'<img src="data:image/webp;base64,{logo_b64}" style="height:60px;width:auto;">'
        f'<span style="font-size:1.75rem;font-weight:700;color:#1798d3;">'
        f'WFA Word Puzzle Generator</span></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown('<span style="font-size:1.75rem;font-weight:700;color:#1798d3;">WFA Word Puzzle Generator</span>', unsafe_allow_html=True)
st.divider()


def parse_words(text):
    if not text.strip():
        return []
    if "," in text:
        return [w.strip() for w in text.split(",") if w.strip()]
    return [w.strip() for w in text.splitlines() if w.strip()]


def api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")


def require_api_key():
    k = api_key()
    if not k:
        st.error("No ANTHROPIC_API_KEY found in Streamlit secrets. Add it via Settings → Secrets.")
        st.stop()
    return k


def require_topic(t):
    if not t.strip():
        st.error("Please enter a topic.")
        st.stop()


def word_chips(words, colour):
    chips = "".join(
        f'<span style="display:inline-block;background:#e8f4fd;color:{colour};'
        f'border:1px solid {colour}55;border-radius:4px;padding:3px 10px;'
        f'margin:3px;font-size:0.85rem;font-weight:600;">{w.title()}</span>'
        for w in sorted(words, key=str.lower)
    )
    return f'<div style="margin-top:6px;">{chips}</div>'


def grid_html(grid, colour):
    rows = ""
    for row in grid:
        cells = "".join(
            '<td style="width:28px;height:28px;text-align:center;vertical-align:middle;'
            'font-family:monospace;font-size:14px;font-weight:700;border:1px solid #ccc;">'
            + letter + "</td>" for letter in row
        )
        rows += f"<tr>{cells}</tr>"
    return (
        '<div style="overflow-x:auto;">'
        f'<table style="border-collapse:collapse;border:2px solid {colour};">'
        + rows + "</table></div>"
    )


def nine_letters_grid_html(letters, required, colour):
    rows = ""
    for r in range(3):
        cells = ""
        for c in range(3):
            idx = r * 3 + c
            letter = letters[idx]
            is_req = idx == 4
            bg = colour if is_req else "#EEF6FB"
            tc = "white" if is_req else colour
            cells += (
                f'<td style="width:52px;height:52px;text-align:center;vertical-align:middle;'
                f'background:{bg};border:2px solid {colour};font-family:monospace;'
                f'font-size:22px;font-weight:700;color:{tc};">{letter}</td>'
            )
        rows += f"<tr>{cells}</tr>"
    return (
        f'<table style="border-collapse:collapse;margin:0 auto;">{rows}</table>'
        f'<div style="font-size:0.8rem;color:gray;margin-top:8px;text-align:center;">'
        f'★ Every word must contain <strong style="color:{colour};">{required}</strong></div>'
    )


def ladder_html(path, colour, show_answers):
    boxes = ""
    for i, word in enumerate(path):
        is_end = i == 0 or i == len(path) - 1
        bg = colour if is_end else "white"
        tc = "white" if is_end else colour
        border = f"2px solid {colour}" if is_end else f"2px dashed {colour}77"
        content = word if (is_end or show_answers) else "&nbsp;" * len(word)
        boxes += (
            f'<div style="width:130px;height:38px;background:{bg};color:{tc};'
            f'border:{border};border-radius:4px;display:flex;align-items:center;'
            f'justify-content:center;font-family:monospace;font-size:16px;'
            f'font-weight:700;margin:0 auto;">{content}</div>'
        )
        if i < len(path) - 1:
            boxes += f'<div style="width:3px;height:12px;background:{colour};margin:0 auto;"></div>'
    return f'<div style="display:flex;flex-direction:column;gap:0;align-items:center;">{boxes}</div>'


def scramble_table_html(items, colour):
    rows = ""
    for i, item in enumerate(items):
        bg = "#F5FBFF" if i % 2 == 0 else "white"
        blanks_html = "&nbsp;".join(
            f'<span style="display:inline-block;width:14px;height:18px;'
            f'border-bottom:2px solid {colour};margin:0 2px;">'
            + (f'<b style="font-size:11px;color:{colour};">{ch}</b>' if ch != "_" else "")
            + "</span>"
            for ch in item["blank_hint"].replace(" ", "")
        )
        rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:7px 8px;font-weight:700;color:{colour};width:28px;">{i+1}.</td>'
            f'<td style="padding:7px 12px;font-family:monospace;font-size:15px;font-weight:700;width:140px;">'
            f'{item["scrambled"]}</td>'
            f'<td style="padding:7px 6px;color:#bbb;width:20px;">→</td>'
            f'<td style="padding:7px 8px;">{blanks_html}</td>'
            f'</tr>'
        )
    return (
        '<div style="overflow-x:auto;">'
        f'<table style="border-collapse:collapse;width:100%;border:1px solid {colour}22;">'
        + rows + "</table></div>"
    )


def cloze_html(passage_with_blanks, word_bank, colour, show_bank):
    def replace_blank(m):
        n = m.group(1)
        return (
            f'<span style="display:inline-block;min-width:70px;border-bottom:2px solid {colour};'
            f'color:{colour};font-size:0.78em;text-align:center;margin:0 3px;padding:0 3px;">'
            f'({n})</span>'
        )
    html = re.sub(r"___(\d+)___", replace_blank, passage_with_blanks)
    out = f'<div style="line-height:2.3;font-size:1rem;">{html}</div>'
    if show_bank and word_bank:
        chips = "".join(
            f'<span style="background:#EEF6FB;color:{colour};border:1px solid {colour}44;'
            f'border-radius:4px;padding:3px 10px;margin:3px;font-size:0.85rem;font-weight:600;'
            f'display:inline-block;">{w.title()}</span>'
            for w in word_bank
        )
        out += f'<div style="margin-top:10px;"><strong>Word bank:</strong> {chips}</div>'
    return out


# ── Controls ──────────────────────────────────────────────────────────────────

PUZZLE_TYPES = ["Word Search", "Nine Letters", "Word Ladder", "Word Scramble", "Cloze Passage"]

puzzle_type = st.selectbox("Puzzle type", PUZZLE_TYPES)
topic = st.text_input("Topic", placeholder="e.g. Anglo-Saxons, Sound, Fractions")

c1, c2 = st.columns(2)
year_group = c1.selectbox("Year group", ["Y1", "Y2", "Y3", "Y4", "Y5", "Y6"], index=3)

words_raw = ""
grid_size = 12
difficulty = "Medium"

if puzzle_type == "Word Search":
    difficulty = c2.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=1,
        help="Easy = left/right and down only · Medium = 4 directions · Hard = all 8 directions")
    grid_size = st.selectbox("Grid size", list(range(8, 21)), index=4, help="Rows × columns")
    words_raw = st.text_area("Word list (optional)", height=90,
        placeholder="One per line or comma-separated. Leave blank to generate from topic.")

elif puzzle_type == "Nine Letters":
    c2.caption("Claude picks a 9-letter word and finds sub-words automatically.")

elif puzzle_type == "Word Ladder":
    difficulty = c2.selectbox("Path length", ["Easy", "Medium", "Hard"], index=1,
        help="Easy = 3–4 steps · Medium = 5–6 steps · Hard = 7–8 steps")

elif puzzle_type == "Word Scramble":
    difficulty = c2.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=1,
        help="Easy = shorter words, first letter shown · Medium = mixed · Hard = longer words")
    words_raw = st.text_area("Word list (optional)", height=90,
        placeholder="One per line or comma-separated. Leave blank to generate from topic.")

elif puzzle_type == "Cloze Passage":
    difficulty = c2.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=1,
        help="Easy/Medium = word bank shown · Hard = no word bank")

st.divider()
generate = st.button("Generate puzzle", type="primary", use_container_width=True)
colour = YEAR_COLOURS.get(year_group, "#1798d3")

# ── Landing ───────────────────────────────────────────────────────────────────

if not generate:
    cols = st.columns(3)
    cards = [
        ("✅ Word Search", "Hidden words in a letter grid. Puzzle + answer page PDF."),
        ("✅ Nine Letters", "3×3 grid — find words using those letters. Every word needs the centre letter."),
        ("✅ Word Ladder", "Change one letter at a time to get from the start word to the end."),
        ("✅ Word Scramble", "Unscramble the jumbled letters to find the hidden word."),
        ("✅ Cloze Passage", "Fill in the missing words in a short passage about the topic."),
    ]
    for i, (h, b) in enumerate(cards[:3]):
        with cols[i]:
            st.markdown(f"#### {h}")
            st.markdown(b)
    ca, cb = st.columns(2)
    with ca:
        st.markdown(f"#### {cards[3][0]}")
        st.markdown(cards[3][1])
    with cb:
        st.markdown(f"#### {cards[4][0]}")
        st.markdown(cards[4][1])
    st.info("Enter a topic above and click **Generate puzzle**.")

# ── Word Search ───────────────────────────────────────────────────────────────

elif puzzle_type == "Word Search":
    if not topic and not words_raw.strip():
        st.error("Please enter a topic or a word list.")
        st.stop()

    with st.spinner("Generating…"):
        words = parse_words(words_raw)
        display_title = topic or "Custom word list"
        clf_words_used = []

        if not words:
            clf_pre, _ = get_clf_words(topic, year_group)
            clf_words_used = [w.upper() for w in clf_pre[:8]]
            key = require_api_key()
            try:
                words, display_title = get_words_from_topic(topic, year_group, "Word Search", n=16, api_key=key)
            except Exception as e:
                st.error(f"Could not generate words: {e}")
                st.stop()

        if not words:
            st.error("No words — try a different topic or add words manually.")
            st.stop()

        grid, placed, failed, positions = generate_word_search(words, size=grid_size, difficulty=difficulty)

    title_str = f"Word Search: {display_title}"
    st.markdown(f"**{title_str}**")
    st.divider()

    col_grid, col_info = st.columns([3, 2], gap="large")
    with col_grid:
        st.markdown(grid_html(grid, colour), unsafe_allow_html=True)
    with col_info:
        st.markdown(f"**Find these {len(placed)} words:**")
        st.markdown(word_chips(placed, colour), unsafe_allow_html=True)
        clf_in = [w for w in clf_words_used if w in placed]
        if clf_in:
            badge = ", ".join(w.title() for w in sorted(clf_in, key=str.lower)[:8])
            st.markdown(
                '<div style="background:#eef7f0;border-left:3px solid #2bae62;'
                'padding:6px 10px;border-radius:4px;font-size:0.82rem;margin-top:8px;">'
                '<b style="color:#2bae62;">📚 CLF curriculum words:</b> ' + badge + "</div>",
                unsafe_allow_html=True,
            )
        if failed:
            with st.expander(f"⚠ {len(failed)} word(s) couldn't fit"):
                st.markdown(", ".join(w.title() for w in failed))
                st.caption("Try a larger grid size or remove very long words.")
        st.divider()
        pdf_bytes = render_word_search_pdf(grid=grid, words=placed, word_positions=positions, title=title_str, year_group=year_group)
        fname = f"word_search_{(topic or 'custom').lower().replace(' ', '_')}.pdf"
        st.download_button("⬇ Download PDF (puzzle + answers)", data=pdf_bytes, file_name=fname, mime="application/pdf", use_container_width=True)
        st.caption(f"Grid: {grid_size}×{grid_size} · {difficulty} · {year_group}")

# ── Nine Letters ──────────────────────────────────────────────────────────────

elif puzzle_type == "Nine Letters":
    require_topic(topic)
    key = require_api_key()

    with st.spinner("Building Nine Letters puzzle…"):
        try:
            puzzle = generate_nine_letters(topic, year_group, key)
        except Exception as e:
            st.error(f"Could not generate puzzle: {e}")
            st.stop()

    st.markdown(f"**Nine Letters: {topic.title()}**")
    st.divider()

    col_grid, col_clues = st.columns([1, 2], gap="large")
    with col_grid:
        st.markdown(nine_letters_grid_html(puzzle["letters"], puzzle["required"], colour), unsafe_allow_html=True)
    with col_clues:
        clue_num = 1
        for length in sorted(puzzle["words_by_length"].keys()):
            entries = puzzle["words_by_length"][length]
            label = f"{'★ ' if length == 9 else ''}{length} letter{'s' if length != 1 else ''}"
            st.markdown(f"**{label}** ({len(entries)})")
            for entry in entries:
                st.markdown(f"{clue_num}. {entry['clue']}")
                clue_num += 1

    st.divider()
    pdf_bytes = render_nine_letters_pdf(puzzle, year_group=year_group)
    fname = f"nine_letters_{topic.lower().replace(' ', '_')}.pdf"
    st.download_button("⬇ Download PDF (puzzle + answers)", data=pdf_bytes, file_name=fname, mime="application/pdf", use_container_width=True)

# ── Word Ladder ───────────────────────────────────────────────────────────────

elif puzzle_type == "Word Ladder":
    require_topic(topic)
    key = require_api_key()

    with st.spinner("Finding a word ladder path…"):
        try:
            puzzle = generate_word_ladder(topic, year_group, difficulty, key)
        except Exception as e:
            st.error(f"Could not generate word ladder: {e}")
            st.stop()

    num_steps = puzzle["num_steps"]
    st.markdown(f"**Word Ladder: {topic.title()}** — {puzzle['start']} → {puzzle['end']} ({num_steps} step{'s' if num_steps != 1 else ''})")
    st.divider()

    col_ladder, col_info = st.columns([1, 2], gap="large")
    with col_ladder:
        st.markdown(ladder_html(puzzle["path"], colour, show_answers=False), unsafe_allow_html=True)
    with col_info:
        st.markdown(
            f"**Start:** {puzzle['start'].title()}  \n"
            f"**End:** {puzzle['end'].title()}  \n"
            f"**Steps:** {num_steps}  \n"
            f"**Word length:** {puzzle['word_length']} letters"
        )
        st.markdown("---")
        st.markdown("**Answer path:**")
        for i, word in enumerate(puzzle["path"]):
            if i == 0:
                st.markdown(f"↳ **{word.title()}** (start)")
            elif i == len(puzzle["path"]) - 1:
                st.markdown(f"↳ **{word.title()}** (end)")
            else:
                st.markdown(f"↳ {word.title()}")

    st.divider()
    pdf_bytes = render_word_ladder_pdf(puzzle, year_group=year_group)
    fname = f"word_ladder_{topic.lower().replace(' ', '_')}.pdf"
    st.download_button("⬇ Download PDF (puzzle + answers)", data=pdf_bytes, file_name=fname, mime="application/pdf", use_container_width=True)

# ── Word Scramble ─────────────────────────────────────────────────────────────

elif puzzle_type == "Word Scramble":
    if not topic and not words_raw.strip():
        st.error("Please enter a topic or a word list.")
        st.stop()

    with st.spinner("Generating…"):
        words = parse_words(words_raw)
        display_title = topic or "Custom word list"

        if not words:
            key = require_api_key()
            try:
                words, display_title = get_words_from_topic(topic, year_group, "Word Scramble", n=15, api_key=key)
            except Exception as e:
                st.error(f"Could not generate words: {e}")
                st.stop()

        if not words:
            st.error("No words — try a different topic or add words manually.")
            st.stop()

        items = generate_word_scramble(words, difficulty=difficulty)

    title_str = f"Word Scramble: {display_title}"
    st.markdown(f"**{title_str}**")
    st.caption(f"{len(items)} words · {difficulty} · {year_group}")
    st.divider()

    st.markdown(scramble_table_html(items, colour), unsafe_allow_html=True)
    st.divider()
    pdf_bytes = render_word_scramble_pdf(items, topic=display_title, year_group=year_group)
    fname = f"word_scramble_{(topic or 'custom').lower().replace(' ', '_')}.pdf"
    st.download_button("⬇ Download PDF (puzzle + answers)", data=pdf_bytes, file_name=fname, mime="application/pdf", use_container_width=True)

# ── Cloze Passage ─────────────────────────────────────────────────────────────

elif puzzle_type == "Cloze Passage":
    require_topic(topic)
    key = require_api_key()

    with st.spinner("Writing cloze passage…"):
        try:
            puzzle = generate_cloze(topic, year_group, difficulty, key)
        except Exception as e:
            st.error(f"Could not generate cloze passage: {e}")
            st.stop()

    title_str = f"Cloze Passage: {topic.title()}"
    bank_note = " · Word bank shown" if puzzle["show_bank"] else " · No word bank"
    st.markdown(f"**{title_str}**")
    st.caption(f"{len(puzzle['blanks'])} gaps · {difficulty}{bank_note} · {year_group}")
    st.divider()

    st.markdown(
        cloze_html(puzzle["passage_with_blanks"], puzzle["word_bank"], colour, puzzle["show_bank"]),
        unsafe_allow_html=True,
    )
    st.divider()

    with st.expander("Show answer passage"):
        st.markdown(puzzle["passage_full"])

    pdf_bytes = render_cloze_pdf(puzzle, year_group=year_group)
    fname = f"cloze_{topic.lower().replace(' ', '_')}.pdf"
    st.download_button("⬇ Download PDF (puzzle + answers)", data=pdf_bytes, file_name=fname, mime="application/pdf", use_container_width=True)
