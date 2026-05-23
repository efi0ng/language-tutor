#!/usr/bin/env python3
"""Generate a 2-page vocabulary worksheet PDF.

Usage:
    venv/bin/python tools/vocab_sheet.py \
        --output temp/vocab_sheet.pdf \
        --words "调查|diàochá" "发现|fāxiàn"
"""

import argparse
import os

from fpdf import FPDF

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FONT = os.path.join(TOOLS_DIR, "NotoSansSC-Regular.ttf")

MARGIN = 15          # mm
ROWS_PER_PAGE = 20
TOTAL_ROWS = 40
ROW_H = 10           # mm
NUM_COL_W = 8        # mm
CONTENT_W = 210 - 2 * MARGIN   # 180 mm
WORD_COL_W = (CONTENT_W - NUM_COL_W) / 2   # 86 mm
TRANS_COL_W = CONTENT_W - NUM_COL_W - WORD_COL_W   # 86 mm

GRAY_LIGHT = (249, 249, 249)
GRAY_MED = (170, 170, 170)
GRAY_DARK = (85, 85, 85)
BLACK = (0, 0, 0)


def _setup_font(pdf, font_path):
    pdf.add_font("NotoSC", "", font_path)
    pdf.add_font("NotoSC", "B", font_path)


def _draw_header(pdf, page_num, y):
    """Draw title + field lines. Returns the y position after the header."""
    # Title
    pdf.set_font("NotoSC", "B", 15)
    pdf.set_text_color(*BLACK)
    pdf.set_xy(MARGIN, y)
    pdf.cell(0, 7, "My Vocabulary", new_x="END", new_y="LAST")

    subtitle = "— What do I recognize?" if page_num == 1 else "continued"
    pdf.set_font("NotoSC", "", 11)
    pdf.set_text_color(*GRAY_DARK)
    pdf.set_x(pdf.get_x() + 3)
    pdf.cell(0, 7, subtitle)
    y += 9

    # Field lines: Name / Language / Date / Level
    fields = ["Name", "Language", "Date", "Level"]
    field_w = CONTENT_W / len(fields)
    label_w = 18  # approximate label width in mm

    pdf.set_font("NotoSC", "", 8)
    pdf.set_text_color(*GRAY_DARK)
    y_field = y + 1
    for i, label in enumerate(fields):
        x = MARGIN + i * field_w
        pdf.set_xy(x, y_field)
        pdf.cell(label_w, 5, label.upper())
        # ruled line
        line_x = x + label_w + 1
        line_end = x + field_w - 2
        pdf.set_draw_color(*GRAY_MED)
        pdf.line(line_x, y_field + 4, line_end, y_field + 4)

    pdf.set_text_color(*BLACK)
    pdf.set_draw_color(*BLACK)
    return y + 11


def _draw_table_header(pdf, y):
    """Draw column labels + thick rule. Returns y after the header row."""
    pdf.set_font("NotoSC", "", 8)
    pdf.set_text_color(*GRAY_DARK)

    pdf.set_xy(MARGIN, y)
    pdf.cell(NUM_COL_W, 6, "#", align="C")
    pdf.set_xy(MARGIN + NUM_COL_W, y)
    pdf.cell(WORD_COL_W, 6, "WORD / PHRASE")
    pdf.set_xy(MARGIN + NUM_COL_W + WORD_COL_W, y)
    pdf.cell(TRANS_COL_W, 6, "TRANSLATION / MEANING")

    y += 6
    pdf.set_draw_color(*BLACK)
    pdf.set_line_width(0.5)
    pdf.line(MARGIN, y, MARGIN + CONTENT_W, y)
    pdf.set_line_width(0.2)
    pdf.set_text_color(*BLACK)
    return y


def _draw_row(pdf, y, row_num, word=None, pinyin=None):
    """Draw one data row. word/pinyin pre-populate the left column if given."""
    # Alternating background
    if row_num % 2 == 0:
        pdf.set_fill_color(*GRAY_LIGHT)
        pdf.rect(MARGIN, y, CONTENT_W, ROW_H, style="F")

    # Row divider
    pdf.set_draw_color(204, 204, 204)
    pdf.line(MARGIN, y + ROW_H, MARGIN + CONTENT_W, y + ROW_H)

    # Row number
    pdf.set_font("NotoSC", "", 8)
    pdf.set_text_color(*GRAY_MED)
    pdf.set_xy(MARGIN, y + (ROW_H - 8 * 0.352778) / 2)
    pdf.cell(NUM_COL_W, 8 * 0.352778, str(row_num), align="C")

    # Vertical divider between word and translation columns
    word_col_end_x = MARGIN + NUM_COL_W + WORD_COL_W
    pdf.set_draw_color(221, 221, 221)
    pdf.line(word_col_end_x, y, word_col_end_x, y + ROW_H)

    # Pre-populated word content
    if word:
        word_x = MARGIN + NUM_COL_W + 2
        if pinyin:
            # Stack: word (12pt) on top, pinyin (9pt, gray) below
            word_h = 12 * 0.352778
            pinyin_h = 9 * 0.352778
            total_h = word_h + pinyin_h + 0.5
            word_y = y + (ROW_H - total_h) / 2

            pdf.set_font("NotoSC", "B", 12)
            pdf.set_text_color(*BLACK)
            pdf.set_xy(word_x, word_y)
            pdf.cell(WORD_COL_W - 4, word_h, word)

            pdf.set_font("NotoSC", "", 9)
            pdf.set_text_color(*GRAY_DARK)
            pdf.set_xy(word_x, word_y + word_h + 0.5)
            pdf.cell(WORD_COL_W - 4, pinyin_h, pinyin)
        else:
            # Single line: word only
            pdf.set_font("NotoSC", "B", 12)
            pdf.set_text_color(*BLACK)
            word_h = 12 * 0.352778
            pdf.set_xy(word_x, y + (ROW_H - word_h) / 2)
            pdf.cell(WORD_COL_W - 4, word_h, word)

    pdf.set_text_color(*BLACK)
    pdf.set_draw_color(*BLACK)


def _draw_footer(pdf, page_num):
    """Draw page number at bottom right."""
    pdf.set_font("NotoSC", "", 8)
    pdf.set_text_color(*GRAY_MED)
    pdf.set_xy(MARGIN, 297 - MARGIN - 5)
    pdf.cell(CONTENT_W, 5, f"Page {page_num}", align="R")
    pdf.set_text_color(*BLACK)


def generate(output, words, font_path=DEFAULT_FONT):
    """Build 2-page vocabulary PDF.

    words: list of (word, pinyin) tuples for pre-populated rows.
           Rows beyond len(words) are blank.
    """
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=False)
    _setup_font(pdf, font_path)
    pdf.set_line_width(0.2)

    for page_num in (1, 2):
        pdf.add_page()
        y = MARGIN

        y = _draw_header(pdf, page_num, y)
        y = _draw_table_header(pdf, y)

        start_row = (page_num - 1) * ROWS_PER_PAGE + 1
        for i in range(ROWS_PER_PAGE):
            row_num = start_row + i
            word_idx = row_num - 1
            if word_idx < len(words):
                w, p = words[word_idx]
                _draw_row(pdf, y, row_num, word=w, pinyin=p or None)
            else:
                _draw_row(pdf, y, row_num)
            y += ROW_H

        _draw_footer(pdf, page_num)

    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    pdf.output(output)
    print(f"Saved: {output}")


def main():
    parser = argparse.ArgumentParser(description="Generate a vocabulary worksheet PDF")
    parser.add_argument("--output", "-o", required=True, help="Output PDF path")
    parser.add_argument(
        "--words", nargs="*", default=[],
        help='Pre-populated words as "WORD|PINYIN" pairs (pinyin may be empty)'
    )
    parser.add_argument("--font", default=DEFAULT_FONT, help="Path to TTF font")
    args = parser.parse_args()

    words = []
    for entry in args.words:
        parts = entry.split("|", 1)
        word = parts[0].strip()
        pinyin = parts[1].strip() if len(parts) > 1 else ""
        if word:
            words.append((word, pinyin))

    generate(args.output, words, font_path=args.font)


if __name__ == "__main__":
    main()
