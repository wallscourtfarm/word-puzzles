"""
WFA Word Puzzle Generator — Streamlit app
Phase 1: Word Search. Further puzzle types coming soon.
"""
import sys
import os
import base64
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from puzzles.word_search import generate_word_search
from pdf_output.word_search_pdf import render_word_search_pdf
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

# ── CSS — WFA blue theme, overrides all Streamlit red ─────────────────────────
# Reused across all WFA Streamlit apps. Primary = #1798d3.
st.markdown("""
<style>
div[data-testid="stMainBlockContainer"] { max-width: 860px; margin: 0 auto; }

/* ── Buttons ── */
div[data-testid="stButton"] button {
    background-color: #1798d3 !important;
    border-color: #1798d3 !important;
    color: #ffffff !important;
}
div[data-testid="stButton"] button:hover {
    background-color: #1280b8 !important;
    border-color: #1280b8 !important;
}
div[data-testid="stDownloadButton"] > button {
    background: #ffffff !important;
    border: 1.5px solid #1798d3 !important;
    color: #1798d3 !important;
}
div[data-testid="stDownloadButton"] > button:hover { background: #f0f8ff !important; }

/* ── Selectbox / multiselect focus border ── */
[data-baseweb="select"] > div {
    border-color: #cccccc !important;
}
[data-baseweb="select"] > div:focus-within {
    border-color: #1798d3 !important;
    box-shadow: 0 0 0 3px #1798d333 !important;
}

/* ── Text input / textarea focus border ── */
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div {
    border-color: #cccccc !important;
}
[data-baseweb="input"] > div:focus-within,
[data-baseweb="textarea"] > div:focus-within {
    border-color: #1798d3 !important;
    box-shadow: 0 0 0 3px #1798d333 !important;
}

/* ── Radio / checkbox active state ── */
[data-baseweb="radio"] [data-checked="true"] > div,
[data-baseweb="checkbox"] [data-checked="true"] > div {
    background-color: #1798d3 !important;
    border-color: #1798d3 !important;
}

/* ── Progress / spinner ── */
div[data-testid="stProgressBar"] > div > div {
    background-color: #1798d3 !important;
}

/* ── Tabs active underline ── */
button[data-baseweb="tab"][aria-selected="true"] {
    border-bottom-color: #1798d3 !important;
    color: #1798d3 !important;
}
</style>
""", unsafe_allow_html=True)


# ── Header — matches reading-generator style ──────────────────────────────────
def _b64_img(path, mime="image/png"):
    return base64.b64encode(Path(path).read_bytes()).decode()

if LOGO_PATH.exists():
    logo_b64 = _b64_img(LOGO_PATH)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:18px;margin-bottom:6px;">'
        f'<img src="data:image/webp;base64,{logo_b64}" style="height:60px;width:auto;">'
        f'<span style="font-size:1.75rem;font-weight:700;color:#1798d3;">'
        f'WFA Word Puzzle Generator</span></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<span style="font-size:1.75rem;font-weight:700;color:#1798d3;">'
        'WFA Word Puzzle Generator</span>',
        unsafe_allow_html=True,
    )
st.divider()


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_words(text):
    if not text.strip():
        return []
    if "," in text:
        return [w.strip() for w in text.split(",") if w.strip()]
    return [w.strip() for w in text.splitlines() if w.strip()]


def grid_html(grid, colour):
    rows = ""
    for row in grid:
        cells = "".join(
            '<td style="width:28px;height:28px;text-align:center;vertical-align:middle;'
            'font-family:monospace;font-size:14px;font-weight:700;border:1px solid #ccc;">'
            + letter + "</td>"
            for letter in row
        )
        rows += f"<tr>{cells}</tr>"
    return (
        '<div style="overflow-x:auto;">'
        f'<table style="border-collapse:collapse;border:2px solid {colour};">'
        + rows + "</table></div>"
    )


def word_chips(words, colour):
    chips = "".join(
        f'<span style="display:inline-block;background:#e8f4fd;color:{colour};'
        f'border:1px solid {colour}55;border-radius:4px;padding:3px 10px;'
        f'margin:3px;font-size:0.85rem;font-weight:600;">{w.title()}</span>'
        for w in sorted(words, key=str.lower)
    )
    return f'<div style="margin-top:6px;">{chips}</div>'


def api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")


# ── Controls ──────────────────────────────────────────────────────────────────

puzzle_type = st.selectbox(
    "Puzzle type",
    [
        "Word Search",
        "Nine Letters (coming soon)",
        "Word Ladder (coming soon)",
        "Word Scramble (coming soon)",
        "Cloze Passage (coming soon)",
    ],
)
st.divider()

topic = st.text_input("Topic", placeholder="e.g. Anglo-Saxons, Sound, Fractions")
words_raw = st.text_area(
    "Word list (optional)",
    placeholder="One per line, or comma-separated.\nLeave blank to generate from topic.",
    height=100,
)

c1, c2, c3 = st.columns(3)
year_group = c1.selectbox("Year group", ["Y1", "Y2", "Y3", "Y4", "Y5", "Y6"], index=3)
difficulty = c2.selectbox(
    "Difficulty",
    options=["Easy", "Medium", "Hard"],
    index=1,
    help="Easy = across/down only · Hard = all 8 directions including diagonals",
)
grid_size = c3.selectbox(
    "Grid size",
    options=list(range(8, 21)),
    index=4,
    help="Rows × columns",
)

st.divider()
generate = st.button("Generate puzzle", type="primary", use_container_width=True)

colour = YEAR_COLOURS.get(year_group, "#1798d3")


# ── Landing state ─────────────────────────────────────────────────────────────

if not generate:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### ✅ Word Search")
        st.markdown(
            "Hidden words in a letter grid. Generates a puzzle sheet "
            "and a separate answer page — ready to print."
        )
    with col2:
        st.markdown("#### 🔜 Nine Letters")
        st.markdown(
            "9-letter grid. Find words of different lengths, each clued — "
            "same format as the morning display Boggle panel."
        )
    with col3:
        st.markdown("#### 🔜 Word Ladder")
        st.markdown(
            "Change one letter at a time to get from the top word to the bottom."
        )
    st.info("Enter a topic above and click **Generate puzzle**.")

elif "coming soon" in puzzle_type:
    st.info(f"**{puzzle_type.split('(')[0].strip()}** is in the build queue — check back soon.")

else:
    # ── Word Search ───────────────────────────────────────────────────────────
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

            key = api_key()
            if not key:
                st.error(
                    "No ANTHROPIC_API_KEY found in Streamlit secrets. "
                    "Add it via Settings → Secrets."
                )
                st.stop()
            try:
                words, display_title = get_words_from_topic(
                    topic, year_group, "Word Search", n=16, api_key=key
                )
            except Exception as e:
                st.error(f"Could not generate words: {e}")
                st.stop()

        if not words:
            st.error("No words to work with — try a different topic or add words manually.")
            st.stop()

        grid, placed, failed, positions = generate_word_search(
            words, size=grid_size, difficulty=difficulty
        )

    title_str = f"Word Search: {display_title}"
    st.markdown(f"**{title_str}**")
    st.divider()

    col_grid, col_info = st.columns([3, 2], gap="large")

    with col_grid:
        st.markdown(grid_html(grid, colour), unsafe_allow_html=True)

    with col_info:
        st.markdown(f"**Find these {len(placed)} words:**")
        st.markdown(word_chips(placed, colour), unsafe_allow_html=True)

        clf_in_puzzle = [w for w in clf_words_used if w in placed]
        if clf_in_puzzle:
            badge_words = ", ".join(
                w.title() for w in sorted(clf_in_puzzle, key=str.lower)[:8]
            )
            st.markdown(
                '<div style="background:#eef7f0;border-left:3px solid #2bae62;'
                'padding:6px 10px;border-radius:4px;font-size:0.82rem;margin-top:8px;">'
                '<b style="color:#2bae62;">📚 CLF curriculum words:</b> '
                + badge_words + "</div>",
                unsafe_allow_html=True,
            )

        if failed:
            with st.expander(f"⚠ {len(failed)} word(s) couldn't fit"):
                st.markdown(", ".join(w.title() for w in failed))
                st.caption("Try a larger grid size, or remove very long words.")

        st.divider()

        pdf_bytes = render_word_search_pdf(
            grid=grid,
            words=placed,
            word_positions=positions,
            title=title_str,
            year_group=year_group,
        )

        fname = f"word_search_{(topic or 'custom').lower().replace(' ', '_')}.pdf"
        st.download_button(
            label="⬇ Download PDF (puzzle + answers)",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            use_container_width=True,
        )
        st.caption(f"Grid: {grid_size}×{grid_size} · {difficulty} · {year_group}")
