# Chinese Flashcard Lightbox — Specification

## Overview

The Chinese flashcard lightbox takes a list of Chinese words and outputs a PDF
where each page is a single flashcard front, sized exactly to match a physical
5" × 3" flashcard.

The PDF is opened on an iPad in a PDF viewer. A blank physical flashcard is
laid over the screen, and the backlight shines the hanzi silhouette through the
card. The user then traces the characters onto the physical card. The iPad
acts as a lightbox — hence the name.

## Creative license

It is OK to solve this problem another way as long as the input (a list of
Chinese words) and the outcome (user can trace characters onto physical
flashcards using the iPad as a lightbox) are preserved.

## Input

- A UTF-8 text file, one Chinese word per line.
- Blank lines are skipped; leading/trailing whitespace is trimmed.
- A "word" is 1+ hanzi. Latin characters or digits mixed in are allowed but not
  the common case.

## Output

- A single PDF.
- Page size: **127 × 76.2 mm** (5" × 3"). One card per page.
- No card outline, no title, no page numbers — just the three elements listed
  below.

### Card elements

1. **Hanzi** — centred horizontally and vertically in the card's inner area
   (card size minus a 3/8" ≈ 9.525 mm border on all sides). Rendered in
   medium-weight `NotoSansSC-Medium.ttf` (already present at
   `tools/NotoSansSC-Medium.ttf`). Solid black fill — produces a clear
   silhouette on the iPad for lightbox tracing.
2. **Pinyin** — small, top-left corner, inset ~4 mm from the card edges. Not
   traced; purely a reading aid.
3. **English gloss** — small, bottom-right corner, inset ~4 mm from the card
   edges, right-aligned. Not traced.

### Multi-hanzi layout

All hanzi in a word sit on a single horizontal row. The font size is chosen
per-word so the row just fits the inner width and height:

- 1 hanzi → very large
- 2–3 hanzi → large
- 4 hanzi → medium
- 5+ hanzi → smaller (still fits; at the extreme, size is clamped at a
  sensible minimum and a warning is emitted).

A sensible maximum font size is also enforced so single-character words don't
blow up to absurd sizes.

## Lookup

Pinyin and English gloss are looked up in `tools/data/cedict_hsk.json` (the
CEDICT data already built for the assessment tool). The first sub-gloss of the
first definition is used for the corner (split on `"; "` and take the first).

If a word is not in CEDICT:

- The card is still generated with the hanzi only; both corners are left
  blank.
- A warning is printed to stderr listing the missing word.

## Font

- Default: `tools/NotoSansSC-Medium.ttf` (medium weight — good silhouette,
  per the spec). Overridable via `--font`.
- Pinyin and gloss use the same font at smaller sizes.

## Delivery

Two pieces:

- **CLI tool**: `tools/flashcard.py`. Minimal flags: `--file`, `--output`,
  `--font`, `--cedict`.
- **Claude Code skill**: `.claude/skills/flashcard/SKILL.md`. Thin wrapper
  that writes the word list to `temp/`, invokes the tool, and cleans up.
