#!/usr/bin/env python3
"""Annotate Chinese text with HSK 3.0 vocabulary levels.

Segments the text using jieba, looks up each word in the HSK 3.0 vocabulary
list, and outputs per-character color annotations for the colored study PDF.

Usage:
    python tools/hsk_annotate.py --file input.txt --reader-level 1 --output annotations.json
    python tools/hsk_annotate.py --text "新华社北京..." --reader-level 1 --output annotations.json

Output JSON:
    {
      "reader_level": 1,
      "annotations": [{"char": "新", "color": null}, {"char": "华", "color": [0, 0, 139]}, ...]
    }

    color is null for chars at/below reader level, or [R, G, B] for above:
      1 level above  → dark blue   [0, 0, 139]
      2 levels above → dark purple [75, 0, 130]
      3+ levels above→ dark red    [139, 0, 0]
    Unknown words (not in HSK) are treated as 3+ levels above.
"""

import argparse
import csv
import json
import os

# Suppress jieba loading messages
import logging
logging.getLogger("jieba").setLevel(logging.ERROR)
import jieba

HSK_CSV = os.path.join(os.path.dirname(__file__), "data", "hsk30.csv")


def _is_cjk(char):
    cp = ord(char)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0xF900 <= cp <= 0xFAFF
        or 0x20000 <= cp <= 0x2A6DF
    )

# RGB colors indexed by distance above reader level (capped at 3)
LEVEL_COLORS = {
    1: [0, 100, 0],     # dark green
    2: [75, 0, 130],    # dark purple
    3: [139, 0, 0],     # dark red
}


def load_hsk_dict():
    """Return dict mapping simplified word → HSK level (int, 1–9)."""
    word_level = {}
    with open(HSK_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            level_str = row["Level"].strip()
            try:
                level = int(level_str)
            except ValueError:
                # "7-9" → treat as 7
                level = int(level_str.split("-")[0])

            # Simplified field may be pipe-separated variants: "爸爸|爸"
            for word in row["Simplified"].split("|"):
                word = word.strip()
                if not word:
                    continue
                # Keep lowest level if a word appears more than once
                if word not in word_level or level < word_level[word]:
                    word_level[word] = level

    return word_level


def get_color(word_level, reader_level):
    """Return RGB list or None for a word at word_level given reader_level."""
    if word_level is None:
        return LEVEL_COLORS[3]  # unknown → dark red
    diff = word_level - reader_level
    if diff <= 0:
        return None
    return LEVEL_COLORS[min(diff, 3)]


def annotate(text, reader_level=1):
    """Return list of {"char": c, "color": [r,g,b]|null} for every char."""
    hsk = load_hsk_dict()

    # Prime jieba with HSK vocabulary so multi-character words are recognized
    jieba.initialize()
    for word in hsk:
        if len(word) > 1:
            jieba.add_word(word, freq=1000)

    result = []
    for line in text.splitlines():
        if result:
            result.append({"char": "\n", "color": None})
        if not line.strip():
            continue
        for segment in jieba.cut(line):
            level = hsk.get(segment)
            if level is not None or len(segment) == 1:
                # Known word or single character: color all chars the same
                # Non-CJK chars (digits, punctuation, Latin) are never colored
                color = get_color(level, reader_level)
                for char in segment:
                    c = None if not _is_cjk(char) else color
                    result.append({"char": char, "color": c})
            else:
                # Multi-char segment not in HSK: fall back to per-character lookup
                for char in segment:
                    if not _is_cjk(char):
                        result.append({"char": char, "color": None})
                    else:
                        char_level = hsk.get(char)
                        result.append({"char": char, "color": get_color(char_level, reader_level)})

    return result


def main():
    parser = argparse.ArgumentParser(description="Annotate Chinese text with HSK levels")
    parser.add_argument("--text", help="Text to annotate")
    parser.add_argument("--file", help="File containing text to annotate")
    parser.add_argument("--reader-level", type=int, default=1,
                        help="Reader's HSK level (default: 1)")
    parser.add_argument("--output", "-o", required=True, help="Output JSON file path")
    args = parser.parse_args()

    if not args.text and not args.file:
        parser.error("Either --text or --file is required")

    text = open(args.file, encoding="utf-8").read() if args.file else args.text
    annotations = annotate(text, args.reader_level)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"reader_level": args.reader_level, "annotations": annotations},
                  f, ensure_ascii=False, indent=2)
    print(f"Saved: {args.output} ({len(annotations)} characters annotated)")


if __name__ == "__main__":
    main()
