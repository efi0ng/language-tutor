#!/usr/bin/env python3
"""PDF generation tool using fpdf2.

Usage:
    python tools/pdf.py --text "小明是学生。" --title "测试" --output story.pdf
    python tools/pdf.py --file story.txt --output story.pdf --title "My Story"
    python tools/pdf.py --file story.txt --output story.pdf --font /path/to/font.ttf

Renders text to a printable PDF with large, clear font suitable for students.
Supports CJK and other Unicode text via TTF fonts.
"""

import argparse
import os
import sys

from fpdf import FPDF

# Noto Sans SC Regular — TrueType outlines (glyf), instanced from variable font at wght=400
DEFAULT_FONT = os.path.join(os.path.dirname(__file__), "NotoSansSC-Regular.ttf")
DEFAULT_FONT_SIZE = 18
TITLE_FONT_SIZE = 26
LINE_SPACING = 1.6  # multiplier for line height


def create_pdf(text: str, output: str, title: str | None = None,
               font_path: str = DEFAULT_FONT, font_size: int = DEFAULT_FONT_SIZE):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    # Register the TTF font for Unicode support (embedded + subsetted by default)
    pdf.add_font("CustomFont", "", font_path)
    pdf.add_font("CustomFont", "B", font_path)

    # Render title if provided
    if title:
        pdf.set_font("CustomFont", "B", TITLE_FONT_SIZE)
        pdf.cell(0, TITLE_FONT_SIZE * LINE_SPACING, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)

    # Render body text
    pdf.set_font("CustomFont", "", font_size)
    line_height = font_size * LINE_SPACING * 0.35  # convert pt to mm approx
    pdf.multi_cell(0, line_height, text)

    pdf.output(output)
    print(f"Saved: {output}")


def main():
    parser = argparse.ArgumentParser(description="Generate a printable PDF from text")
    parser.add_argument("--text", help="Text to render")
    parser.add_argument("--file", help="File containing text to render")
    parser.add_argument("--output", "-o", required=True, help="Output PDF file path")
    parser.add_argument("--title", help="Title rendered at the top of the PDF")
    parser.add_argument("--font", default=DEFAULT_FONT, help=f"Path to TTF font (default: {DEFAULT_FONT})")
    parser.add_argument("--font-size", type=int, default=DEFAULT_FONT_SIZE,
                        help=f"Body font size in pt (default: {DEFAULT_FONT_SIZE})")

    args = parser.parse_args()

    if not args.text and not args.file:
        parser.error("Either --text or --file is required")

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = args.text

    create_pdf(text, args.output, title=args.title,
               font_path=args.font, font_size=args.font_size)


if __name__ == "__main__":
    main()
