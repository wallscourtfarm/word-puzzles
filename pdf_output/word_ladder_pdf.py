"""
Word Ladder PDF renderer.
Page 1: ladder with start/end filled, intermediate rungs blank.
Page 2: complete solved ladder.
"""
import io
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, black

from .pdf_utils import (
    PAGE_W, PAGE_H, MARGIN, HEADER_H,
    year_colour, hex_colour,
    draw_header, draw_footer, content_top,
)

BOX_W = 140     # box width in points
BOX_H = 32      # box height
GAP = 10        # vertical gap between boxes
STILE_W = 3     # ladder stile line width


def _draw_ladder(c, path: list[str], colour: str, top_y: float, show_answers: bool) -> None:
    """Draw the word ladder centred on the page."""
    n = len(path)
    total_h = n * BOX_H + (n - 1) * GAP
    bx = (PAGE_W - BOX_W) / 2  # left x of boxes
    stile_x_left = bx - 16
    stile_x_right = bx + BOX_W + 16
    start_y = top_y  # top of first box

    for i, word in enumerate(path):
        by = start_y - i * (BOX_H + GAP)  # top of this box
        is_first = i == 0
        is_last = i == n - 1
        is_filled = is_first or is_last or show_answers

        # Box fill
        if is_first or is_last:
            c.setFillColor(hex_colour(colour))
        elif show_answers:
            c.setFillColor(HexColor("#EEF6FB"))
        else:
            c.setFillColor(white)

        c.rect(bx, by - BOX_H, BOX_W, BOX_H, fill=1, stroke=0)

        # Box border
        c.setStrokeColor(hex_colour(colour))
        c.setLineWidth(2 if (is_first or is_last) else 1)
        if not (is_first or is_last):
            # dashed border for blank rungs
            c.setDash(4, 3)
        c.rect(bx, by - BOX_H, BOX_W, BOX_H, fill=0, stroke=1)
        c.setDash()  # reset dash

        # Word text
        if is_filled:
            text = word
        else:
            # Show letter boxes as underscores
            text = "  ".join("_" for _ in word)

        fs = 16 if (is_first or is_last) else 14
        c.setFont("Helvetica-Bold", fs)
        c.setFillColor(white if (is_first or is_last) else hex_colour(colour))
        tw = c.stringWidth(text, "Helvetica-Bold", fs)
        c.drawString(bx + (BOX_W - tw) / 2, by - BOX_H + (BOX_H - fs) / 2 + 2, text)

        # Stile connectors (not below last box)
        if i < n - 1:
            connector_top = by - BOX_H
            connector_bot = connector_top - GAP
            c.setStrokeColor(hex_colour(colour))
            c.setLineWidth(STILE_W)
            c.line(stile_x_left, connector_top, stile_x_left, connector_bot)
            c.line(stile_x_right, connector_top, stile_x_right, connector_bot)

        # Step label on the right (puzzle page only)
        if not show_answers and not is_first and not is_last:
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(0.6, 0.6, 0.6)
            c.drawString(bx + BOX_W + 24, by - BOX_H + BOX_H / 2 - 4, f"Step {i}")


def render_word_ladder_pdf(puzzle: dict, year_group: str = "Y4") -> bytes:
    colour = year_colour(year_group)
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)

    path = puzzle["path"]
    topic = puzzle.get("topic", "")
    num_steps = puzzle["num_steps"]
    title = f"Word Ladder: {topic.title()}"

    for page in ("puzzle", "answers"):
        subtitle = (
            "Answers" if page == "answers"
            else f"Change one letter at a time — {num_steps} step{'s' if num_steps != 1 else ''} to get there"
        )
        draw_header(c, title, subtitle, colour)
        draw_footer(c)

        top = content_top() - 6
        _draw_ladder(c, path, colour, top, show_answers=(page == "answers"))

        # Instruction at bottom of puzzle page
        if page == "puzzle":
            n = len(path)
            total_h = n * BOX_H + (n - 1) * GAP
            bottom_y = top - total_h - 20
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColorRGB(0.45, 0.45, 0.45)
            c.drawCentredString(
                PAGE_W / 2, bottom_y,
                "Change one letter on each rung. Every rung must be a real English word.",
            )

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()
