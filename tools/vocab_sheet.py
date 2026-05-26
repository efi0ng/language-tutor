#!/usr/bin/env python3
"""Generate a vocabulary reference list PDF.

Usage:
    venv/bin/python tools/vocab_sheet.py \
        --output temp/vocab_sheet.pdf \
        --words "调查|diàochá|investigate" "发现|fāxiàn|discover" \
        --title "AI Lab Mystery"
"""

import argparse
import math
import os

from fpdf import FPDF

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FONT = os.path.join(TOOLS_DIR, "NotoSansSC-Regular.ttf")

PAGE_W = 210
PAGE_H = 297
MARGIN = 15
CONTENT_W = PAGE_W - 2 * MARGIN   # 180mm
COL_GAP = 5
COL_W = (CONTENT_W - COL_GAP) / 2  # 87.5mm

WORD_COL_W = 48       # mm — word/pinyin sub-column
TRANS_COL_W = COL_W - WORD_COL_W   # 39.5mm — translation sub-column

CJK_ROW_H = 12   # mm — hanzi + pinyin stacked
LATIN_ROW_H = 8  # mm — single line

GRAY_LIGHT = (247, 247, 247)
GRAY_DARK = (100, 100, 100)
GRAY_SEP = (210, 210, 210)
BLACK = (0, 0, 0)

FONT_NAME = "NotoSC"


def _setup_font(pdf, font_path):
    pdf.add_font(FONT_NAME, "", font_path)
    pdf.add_font(FONT_NAME, "B", font_path)


def _draw_header(pdf, title, y):
    """Draw "Vocabulary" heading and optional story subtitle. Returns y after header."""
    pdf.set_font(FONT_NAME, "B", 14)
    pdf.set_text_color(*BLACK)
    pdf.set_xy(MARGIN, y)
    pdf.cell(0, 7, "Vocabulary")
    y += 8

    if title:
        pdf.set_font(FONT_NAME, "", 9)
        pdf.set_text_color(*GRAY_DARK)
        pdf.set_xy(MARGIN, y)
        pdf.cell(0, 5, title)
        y += 6

    pdf.set_draw_color(*GRAY_SEP)
    pdf.set_line_width(0.3)
    pdf.line(MARGIN, y, MARGIN + CONTENT_W, y)
    pdf.set_line_width(0.2)
    pdf.set_draw_color(*BLACK)
    return y + 3


def _draw_column(pdf, col_x, y_start, words_slice, row_h):
    """Render a list of (word, pinyin, translation) tuples as a two-sub-column block."""
    is_cjk = any(p for _, p, _ in words_slice)

    for i, (word, pinyin, translation) in enumerate(words_slice):
        y = y_start + i * row_h

        if i % 2 == 1:
            pdf.set_fill_color(*GRAY_LIGHT)
            pdf.rect(col_x, y, COL_W, row_h, style="F")

        pdf.set_draw_color(*GRAY_SEP)
        pdf.set_line_width(0.15)
        pdf.line(col_x, y + row_h, col_x + COL_W, y + row_h)

        div_x = col_x + WORD_COL_W
        pdf.line(div_x, y, div_x, y + row_h)

        word_x = col_x + 2

        if is_cjk and pinyin:
            hanzi_pt, pinyin_pt = 11, 8
            hanzi_h = hanzi_pt * 0.352778
            pinyin_h = pinyin_pt * 0.352778
            stack_h = hanzi_h + 0.8 + pinyin_h
            word_y = y + (row_h - stack_h) / 2

            pdf.set_font(FONT_NAME, "B", hanzi_pt)
            pdf.set_text_color(*BLACK)
            pdf.set_xy(word_x, word_y)
            pdf.cell(WORD_COL_W - 3, hanzi_h, word)

            pdf.set_font(FONT_NAME, "", pinyin_pt)
            pdf.set_text_color(*GRAY_DARK)
            pdf.set_xy(word_x, word_y + hanzi_h + 0.8)
            pdf.cell(WORD_COL_W - 3, pinyin_h, pinyin)
        else:
            word_pt = 10
            word_h_mm = word_pt * 0.352778
            pdf.set_font(FONT_NAME, "B", word_pt)
            pdf.set_text_color(*BLACK)
            pdf.set_xy(word_x, y + (row_h - word_h_mm) / 2)
            pdf.cell(WORD_COL_W - 3, word_h_mm, word)

        trans_pt = 9
        trans_h_mm = trans_pt * 0.352778
        pdf.set_font(FONT_NAME, "", trans_pt)
        pdf.set_text_color(*GRAY_DARK)
        pdf.set_xy(div_x + 2, y + (row_h - trans_h_mm) / 2)
        pdf.cell(TRANS_COL_W - 2, trans_h_mm, translation)

    pdf.set_draw_color(*BLACK)
    pdf.set_text_color(*BLACK)
    pdf.set_line_width(0.2)


def generate(output, words, title=None, font_path=DEFAULT_FONT):
    """Build vocabulary reference PDF.

    words: list of (word, pinyin, translation) tuples.
    """
    is_cjk = any(p for _, p, _ in words) if words else False
    row_h = CJK_ROW_H if is_cjk else LATIN_ROW_H

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=False)
    _setup_font(pdf, font_path)

    header_h = 8 + (6 if title else 0) + 3
    available_h = PAGE_H - 2 * MARGIN - header_h
    rows_per_col = int(available_h / row_h)
    words_per_page = rows_per_col * 2

    num_pages = max(1, math.ceil(len(words) / words_per_page)) if words else 1
    col_x = [MARGIN, MARGIN + COL_W + COL_GAP]

    for page_num in range(1, num_pages + 1):
        pdf.add_page()
        y_content = _draw_header(pdf, title, MARGIN)

        page_words = words[(page_num - 1) * words_per_page: page_num * words_per_page]
        left_words = page_words[:rows_per_col]
        right_words = page_words[rows_per_col:]

        if left_words:
            _draw_column(pdf, col_x[0], y_content, left_words, row_h)
        if right_words:
            _draw_column(pdf, col_x[1], y_content, right_words, row_h)

    out_dir = os.path.dirname(os.path.abspath(output))
    os.makedirs(out_dir, exist_ok=True)
    pdf.output(output)
    print(f"Saved: {output}")


def main():
    parser = argparse.ArgumentParser(description="Generate a vocabulary reference list PDF")
    parser.add_argument("--output", "-o", required=True, help="Output PDF path")
    parser.add_argument(
        "--words", nargs="*", default=[],
        help='Words as "WORD|PINYIN|TRANSLATION" (use "WORD||TRANSLATION" when no pinyin)'
    )
    parser.add_argument("--title", default=None, help="Story name shown as subtitle")
    parser.add_argument("--font", default=DEFAULT_FONT, help="Path to TTF font")
    args = parser.parse_args()

    words = []
    for entry in args.words:
        parts = entry.split("|", 2)
        word = parts[0].strip()
        pinyin = parts[1].strip() if len(parts) > 1 else ""
        translation = parts[2].strip() if len(parts) > 2 else ""
        if word:
            words.append((word, pinyin, translation))

    generate(args.output, words, title=args.title, font_path=args.font)


if __name__ == "__main__":
    main()
