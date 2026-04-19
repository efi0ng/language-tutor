# Flashcard Lightbox Skill

## Activation

This skill activates when the user asks to make tracing flashcards, lightbox
flashcards, a PDF for tracing Chinese characters onto physical flashcards, or
similar phrasings. The goal is to produce a PDF the user can open on an iPad
and lay blank physical flashcards over, so the backlit hanzi silhouettes can
be traced onto the cards.

## Inputs (derive from the user's prompt)

- **words**: The list of Chinese words. May be given inline ("make flashcards
  for 你好, 谢谢, 再见"), as a paste, or referenced from a file.
- **output_path**: Where to save the PDF. Default:
  `materials/chinese/flashcards/{slug}.pdf` where `{slug}` is a short name
  derived from context (e.g. `hsk1_week3`). Create the directory if missing.

## Procedure

1. Write the word list to `temp/flashcard_words.txt`, one word per line, no
   punctuation, no blank lines.
2. Ensure the output directory exists:
   ```bash
   mkdir -p $(dirname {output_path})
   ```
3. Run the tool:
   ```bash
   venv/bin/python tools/flashcard.py \
     --file temp/flashcard_words.txt \
     --output {output_path}
   ```
4. Clean up `temp/flashcard_words.txt`.
5. Report the output path, number of cards, and any words the tool flagged as
   missing from CEDICT (hanzi-only cards).

## Notes

- `tools/data/cedict_hsk.json` is HSK-scoped. Compound phrases that aren't
  distinct HSK entries (e.g. `你好`) will be rendered as hanzi-only cards with
  a warning — this is expected and still usable for tracing. Relay the warning
  to the user in your final report so they know which cards have no pinyin/gloss.
- The PDF is intended to be viewed one card at a time on the iPad. Do not try
  to tile multiple cards per page — each page is exactly the physical card
  size (5" × 3").
