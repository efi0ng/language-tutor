#!/usr/bin/env python3
"""Generate a PDF of 5x3-inch flashcard fronts for tracing.

Usage:
    venv/bin/python tools/flashcard.py --file words.txt --output flashcards.pdf

Each input line is one Chinese word. Each PDF page is exactly one flashcard
(5" x 3", landscape) with the hanzi centred and auto-sized to fit, plus small
pinyin (top-left) and English gloss (bottom-right) looked up from CEDICT.

The PDF is designed to be opened on an iPad in a PDF viewer. A blank physical
flashcard laid over the screen lets the user trace the hanzi silhouette
through the card.
"""

import argparse
import json
import os
import sys

from fpdf import FPDF

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FONT = os.path.join(TOOLS_DIR, "NotoSansSC-Medium.ttf")
DEFAULT_CEDICT = os.path.join(TOOLS_DIR, "data", "cedict_hsk.json")

# Card geometry (mm). 5" x 3" = 127 x 76.2 mm.
CARD_W = 127.0
CARD_H = 76.2
BORDER = 9.525  # 3/8 inch

# Corner text.
CORNER_INSET = 4.0         # mm from card edge
PINYIN_PT = 11
GLOSS_PT = 9
GLOSS_MAX_CHARS = 40

# Hanzi sizing bounds (pt).
HANZI_PT_MIN = 40
HANZI_PT_MAX = 220

# Padding between hanzi area and corner text rows (mm).
CORNER_PAD = 2.0

PT_TO_MM = 0.352778  # 1 pt in mm


def load_cedict(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def lookup(cedict, word):
    """Return (pinyin, short_gloss) or (None, None) if missing."""
    entry = cedict.get(word)
    if not entry:
        return None, None
    pinyin = entry.get("pinyin") or None
    defs = entry.get("definitions") or []
    gloss = None
    if defs:
        first = defs[0].split("; ")[0].strip()
        if len(first) > GLOSS_MAX_CHARS:
            first = first[: GLOSS_MAX_CHARS - 1].rstrip() + "…"
        gloss = first or None
    return pinyin, gloss


def compute_hanzi_pt(n_chars, avail_w_mm, avail_h_mm):
    """Largest pt size so n_chars fit on one row within avail box.

    CJK advance ≈ em-square ≈ font_size_pt * PT_TO_MM per char.
    Height ≈ font_size_pt * PT_TO_MM.
    """
    if n_chars < 1:
        return HANZI_PT_MIN
    pt_by_width = avail_w_mm / (n_chars * PT_TO_MM)
    pt_by_height = avail_h_mm / PT_TO_MM
    pt = min(pt_by_width, pt_by_height, HANZI_PT_MAX)
    return max(pt, HANZI_PT_MIN)


def render(words, cedict, font_path, output):
    pdf = FPDF(unit="mm", format=(CARD_W, CARD_H))
    pdf.set_auto_page_break(auto=False)
    pdf.add_font("NotoSC", "", font_path)

    inner_w = CARD_W - 2 * BORDER
    # Height available for hanzi after reserving corner text rows.
    corner_row_mm = max(PINYIN_PT, GLOSS_PT) * PT_TO_MM + CORNER_PAD
    inner_h = CARD_H - 2 * BORDER - 2 * corner_row_mm

    missing = []
    overflow = []

    for word in words:
        pinyin, gloss = lookup(cedict, word)
        if pinyin is None and gloss is None:
            missing.append(word)

        pdf.add_page()

        n = len(word)
        hanzi_pt = compute_hanzi_pt(n, inner_w, inner_h)
        hanzi_w_mm = n * hanzi_pt * PT_TO_MM
        hanzi_h_mm = hanzi_pt * PT_TO_MM
        if hanzi_w_mm > inner_w + 0.01:
            overflow.append(word)

        # Pinyin — top-left.
        if pinyin:
            pdf.set_font("NotoSC", "", PINYIN_PT)
            pdf.set_xy(CORNER_INSET, CORNER_INSET)
            pdf.cell(inner_w, PINYIN_PT * PT_TO_MM, pinyin, align="L")

        # Gloss — bottom-right.
        if gloss:
            pdf.set_font("NotoSC", "", GLOSS_PT)
            gloss_h_mm = GLOSS_PT * PT_TO_MM
            y = CARD_H - CORNER_INSET - gloss_h_mm
            pdf.set_xy(CORNER_INSET, y)
            pdf.cell(CARD_W - 2 * CORNER_INSET, gloss_h_mm, gloss, align="R")

        # Hanzi — centred in the card (using full card centre, not the reduced
        # inner_h box; corner text rows are small enough not to collide in
        # practice and centring on the card reads better).
        pdf.set_font("NotoSC", "", hanzi_pt)
        x = (CARD_W - hanzi_w_mm) / 2
        y = (CARD_H - hanzi_h_mm) / 2
        pdf.set_xy(x, y)
        pdf.cell(hanzi_w_mm, hanzi_h_mm, word, align="C")

    pdf.output(output)
    return missing, overflow


def read_words(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="Generate a tracing-flashcard PDF from a list of Chinese words"
    )
    parser.add_argument("--file", required=True, help="Text file, one word per line")
    parser.add_argument("--output", "-o", required=True, help="Output PDF path")
    parser.add_argument("--font", default=DEFAULT_FONT, help=f"TTF font path (default: {DEFAULT_FONT})")
    parser.add_argument("--cedict", default=DEFAULT_CEDICT, help=f"CEDICT JSON path (default: {DEFAULT_CEDICT})")
    args = parser.parse_args()

    words = read_words(args.file)
    if not words:
        parser.error(f"No words found in {args.file}")

    cedict = load_cedict(args.cedict)
    missing, overflow = render(words, cedict, args.font, args.output)

    print(f"Saved: {args.output} ({len(words)} card{'s' if len(words) != 1 else ''})")
    if missing:
        print(
            f"Warning: {len(missing)} word(s) not in CEDICT — rendered hanzi only: "
            + ", ".join(missing),
            file=sys.stderr,
        )
    if overflow:
        print(
            f"Warning: {len(overflow)} word(s) exceeded the inner border at minimum size: "
            + ", ".join(overflow),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
