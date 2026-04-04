#!/usr/bin/env python3
"""PDF generation tool using fpdf2.

Usage:
    python tools/pdf.py --text "小明是学生。" --title "测试" --output story.pdf
    python tools/pdf.py --file story.txt --output story.pdf --title "My Story"
    python tools/pdf.py --file story.txt --output story.pdf --font /path/to/font.ttf
    python tools/pdf.py --file story.txt --output story.pdf --mode study

Renders text to a printable PDF with large, clear font suitable for students.
Supports CJK and other Unicode text via TTF fonts.

Modes:
    read  (default): Normal flowing text. Good for reading the story.
    study: Layout with writing space. CJK text gets a character grid with per-cell
           pinyin space and a full-width English translation line every row. Latin
           text gets each source line followed by a ruled blank line for translation.
"""

import argparse
import os

from fpdf import FPDF

# Noto Sans SC Bold — TrueType outlines (glyf), instanced from variable font at wght=700
DEFAULT_FONT = os.path.join(os.path.dirname(__file__), "NotoSansSC-Bold.ttf")
DEFAULT_FONT_SIZE = 14
TITLE_FONT_SIZE = 22
LINE_SPACING = 1.6

# Study mode — CJK grid dimensions (mm)
CELL_W = 14          # cell width for CJK characters
STUDY_FONT_SIZE = 30  # pt, for CJK characters in study mode
# Punctuation cell = full em-square advance width + 1mm padding, so align="C" works cleanly
PUNCT_W = round(STUDY_FONT_SIZE * 0.352778) + 1  # ≈ 11mm at 30pt
HANZI_H = 14   # hanzi row height (square cells)
PINYIN_H = 8   # pinyin row height (blank, for handwriting)
ENG_H = 8      # English translation row height (ruled line at bottom)

MARGIN = 15  # page margin (mm) used in all modes


def is_cjk(char):
    cp = ord(char)
    return (
        0x4E00 <= cp <= 0x9FFF    # CJK Unified Ideographs
        or 0x3400 <= cp <= 0x4DBF  # CJK Extension A
        or 0xF900 <= cp <= 0xFAFF  # CJK Compatibility
        or 0x20000 <= cp <= 0x2A6DF  # CJK Extension B
    )


def _cell_w(char):
    return CELL_W if is_cjk(char) else PUNCT_W


def _has_cjk(text):
    return any(is_cjk(c) for c in text)


def _setup_font(pdf, font_path):
    pdf.add_font("CustomFont", "", font_path)
    pdf.add_font("CustomFont", "B", font_path)


# ---------------------------------------------------------------------------
# Read mode
# ---------------------------------------------------------------------------

def create_pdf(text, output, title=None, font_path=DEFAULT_FONT, font_size=DEFAULT_FONT_SIZE):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=MARGIN)
    pdf.add_page()
    _setup_font(pdf, font_path)

    if title:
        pdf.set_font("CustomFont", "B", TITLE_FONT_SIZE)
        pdf.cell(0, TITLE_FONT_SIZE * LINE_SPACING * 0.35, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)

    pdf.set_font("CustomFont", "", font_size)
    line_height = font_size * LINE_SPACING * 0.35
    pdf.multi_cell(0, line_height, text)
    pdf.output(output)
    print(f"Saved: {output}")


# ---------------------------------------------------------------------------
# Study mode — CJK grid
# ---------------------------------------------------------------------------

def _split_into_rows(text, content_w):
    """Split text into display rows.

    Returns a list where each entry is either:
    - A list of characters (one row of the grid), or
    - None (marks a natural line break / paragraph gap from the source text).
    """
    rows = []
    for line in text.split("\n"):
        if not line.strip():
            rows.append(None)
            continue

        current_row = []
        current_w = 0
        for char in line:
            if char in " \t":
                continue  # spaces are meaningless in CJK flow
            cw = _cell_w(char)
            if current_w + cw > content_w and current_row:
                rows.append(current_row)
                current_row = []
                current_w = 0
            current_row.append(char)
            current_w += cw

        if current_row:
            rows.append(current_row)

    return rows


def _draw_cjk_row_group(pdf, chars, y, content_w, font_size):
    """Draw one 3-row group: hanzi | pinyin | English line."""
    # Vertical offset to center text within the hanzi cell.
    # fpdf2 places text at the baseline; we nudge down so the glyph sits centred.
    font_h_mm = font_size * 0.352778  # pt → mm
    v_offset = (HANZI_H - font_h_mm) / 2

    x = MARGIN

    # --- Hanzi row ---
    pdf.set_font("CustomFont", "", font_size)
    for char in chars:
        cw = _cell_w(char)
        pdf.rect(x, y, cw, HANZI_H)
        pdf.set_xy(x, y + v_offset)
        pdf.cell(cw, font_h_mm, char, align="C")
        x += cw
    # Fill remainder so the row always spans full content width
    remainder = MARGIN + content_w - x
    if remainder > 0:
        pdf.rect(x, y, remainder, HANZI_H)

    # --- Pinyin row (blank cells, same column structure) ---
    x = MARGIN
    for char in chars:
        cw = _cell_w(char)
        pdf.rect(x, y + HANZI_H, cw, PINYIN_H)
        x += cw
    remainder = MARGIN + content_w - x
    if remainder > 0:
        pdf.rect(x, y + HANZI_H, remainder, PINYIN_H)

    # --- English row (full-width ruled line at bottom) ---
    y_eng_bottom = y + HANZI_H + PINYIN_H + ENG_H
    pdf.line(MARGIN, y_eng_bottom, MARGIN + content_w, y_eng_bottom)


def create_study_cjk_pdf(text, output, title=None, font_path=DEFAULT_FONT, font_size=STUDY_FONT_SIZE):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False, margin=MARGIN)
    pdf.add_page()
    _setup_font(pdf, font_path)

    content_w = pdf.w - 2 * MARGIN
    y = MARGIN

    if title:
        pdf.set_font("CustomFont", "B", TITLE_FONT_SIZE)
        pdf.set_xy(MARGIN, y)
        pdf.cell(content_w, 8, title, align="L")
        y += 12

    group_h = HANZI_H + PINYIN_H + ENG_H
    rows = _split_into_rows(text, content_w)

    for row in rows:
        if row is None:
            y += 4  # paragraph gap
            continue
        if y + group_h > pdf.h - MARGIN:
            pdf.add_page()
            y = MARGIN
        _draw_cjk_row_group(pdf, row, y, content_w, font_size)
        y += group_h

    pdf.output(output)
    print(f"Saved: {output}")


# ---------------------------------------------------------------------------
# Study mode — Latin script
# ---------------------------------------------------------------------------

def create_study_latin_pdf(text, output, title=None, font_path=DEFAULT_FONT, font_size=DEFAULT_FONT_SIZE):
    RULED_GAP = 2   # mm between end of text and ruled line
    RULED_H = 8     # mm height of blank translation area (line drawn at bottom)
    POST_LINE = 4   # mm gap after ruled line before next text line

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=MARGIN)
    pdf.add_page()
    _setup_font(pdf, font_path)

    content_w = pdf.w - 2 * MARGIN
    line_h = font_size * LINE_SPACING * 0.35

    if title:
        pdf.set_font("CustomFont", "B", TITLE_FONT_SIZE)
        pdf.cell(0, 9, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

    pdf.set_font("CustomFont", "", font_size)

    for line in text.split("\n"):
        if not line.strip():
            pdf.ln(4)
            continue
        pdf.multi_cell(0, line_h, line)
        y = pdf.get_y() + RULED_GAP
        pdf.line(MARGIN, y + RULED_H, MARGIN + content_w, y + RULED_H)
        pdf.set_y(y + RULED_H + POST_LINE)

    pdf.output(output)
    print(f"Saved: {output}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate a printable PDF from text")
    parser.add_argument("--text", help="Text to render")
    parser.add_argument("--file", help="File containing text to render")
    parser.add_argument("--output", "-o", required=True, help="Output PDF file path")
    parser.add_argument("--title", help="Title rendered at the top of the PDF")
    parser.add_argument("--font", default=DEFAULT_FONT, help=f"Path to TTF font (default: {DEFAULT_FONT})")
    parser.add_argument("--font-size", type=int, help="Body font size in pt")
    parser.add_argument("--mode", choices=["read", "study"], default="read",
                        help="read: normal text; study: writing-space layout (default: read)")

    args = parser.parse_args()

    if not args.text and not args.file:
        parser.error("Either --text or --file is required")

    text = open(args.file, encoding="utf-8").read() if args.file else args.text

    if args.mode == "study":
        if _has_cjk(text):
            font_size = args.font_size or STUDY_FONT_SIZE
            create_study_cjk_pdf(text, args.output, title=args.title,
                                  font_path=args.font, font_size=font_size)
        else:
            font_size = args.font_size or DEFAULT_FONT_SIZE
            create_study_latin_pdf(text, args.output, title=args.title,
                                    font_path=args.font, font_size=font_size)
    else:
        font_size = args.font_size or DEFAULT_FONT_SIZE
        create_pdf(text, args.output, title=args.title,
                   font_path=args.font, font_size=font_size)


if __name__ == "__main__":
    main()
