#!/usr/bin/env python3
"""Merge story PDFs into a single student pack PDF.

Usage:
    venv/bin/python tools/pack.py \
        --story-dir materials/chinese/stories/HSK2/ai_lab_mystery_2 \
        --vocab-pdf temp/vocab_sheet.pdf \
        --output outbox/chinese_HSK2_ai_lab_mystery_2_pack.pdf
"""

import argparse
import os
import sys

from pypdf import PdfWriter


def merge(story_dir, vocab_pdf, output):
    parts = [
        os.path.join(story_dir, "story.pdf"),
        vocab_pdf,
        os.path.join(story_dir, "story_study.pdf"),
        os.path.join(story_dir, "questions.pdf"),
    ]

    missing = [p for p in parts if not os.path.exists(p)]
    if missing:
        for p in missing:
            print(f"ERROR: missing file: {p}", file=sys.stderr)
        sys.exit(1)

    writer = PdfWriter()
    for path in parts:
        writer.append(path)

    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    with open(output, "wb") as f:
        writer.write(f)
    print(f"Saved: {output}  ({len(writer.pages)} pages)")


def main():
    parser = argparse.ArgumentParser(description="Merge story PDFs into a student pack")
    parser.add_argument("--story-dir", "-d", required=True, help="Path to story directory")
    parser.add_argument("--vocab-pdf", required=True, help="Path to generated vocabulary sheet PDF")
    parser.add_argument("--output", "-o", required=True, help="Output merged PDF path")
    args = parser.parse_args()
    merge(args.story_dir, args.vocab_pdf, args.output)


if __name__ == "__main__":
    main()
