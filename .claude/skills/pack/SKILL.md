# Student Pack Skill

## Activation

This skill activates when the user asks to create, assemble, generate, or print
a student pack for a story. Look for: "make a pack", "assemble a student pack",
"print pack", "generate a pack", or `/pack`.

## Inputs

Derive from user's prompt or conversation context:

- **story_dir**: Path to the story directory, e.g.
  `materials/chinese/stories/HSK2/ai_lab_mystery_2`. Construct from
  language + level + story name if the user doesn't give a full path.
- **language**: Folder name from the materials path (e.g. `chinese`, `english`).
  Used in the output filename.
- **level**: Level folder name (e.g. `HSK2`, `A1`). Used in the output filename.
- **story_name**: Leaf directory name. Used in the output filename.
- **word_count**: Number of vocabulary words to pre-populate on the vocabulary
  sheet. Default: **5**. Accept a different number if the user specifies one.

## Pre-flight checks

Before starting, verify these three files exist inside `{story_dir}`:
- `story.pdf`
- `story_study.pdf`
- `questions.pdf`

If any is missing, tell the user which file is absent and that they can generate
it by running the story skill, then stop.

## Procedure

### Step 1 — Read the story vocabulary

Read `{story_dir}/story.md`. Locate the vocabulary table (under the
`## Vocabulary` heading or similar). It has columns: Word | Pinyin/Reading |
English (exact column names vary by language).

### Step 2 — Select the top `word_count` words

Choose the **`word_count` words a student most needs to know** to understand
this story. Apply these criteria in order:

1. **Story centrality** — words that appear multiple times or carry the core
   plot/meaning.
2. **Level-appropriate challenge** — prefer words at or just above the stated
   level; these are the teachable gap. Skip trivially simple words the student
   almost certainly already knows.
3. **Concrete and memorable** — concrete nouns and key verbs over generic
   connectives.

For Chinese stories, extract both the Word column and the Pinyin column.
For Latin-script languages (English, French, Spanish, etc.), set pinyin to an
empty string.

Build a list of exactly `word_count` entries in the form `"WORD|PINYIN"` (or
`"WORD|"` when there is no romanisation).

### Step 3 — Generate the vocabulary sheet

```bash
venv/bin/python tools/vocab_sheet.py \
  --output temp/vocab_sheet.pdf \
  --words "W1|P1" "W2|P2" ...
```

Pass all selected words as separate quoted `--words` arguments. If a word has
no pinyin, pass `"WORD|"`.

### Step 4 — Merge the pack

Construct the output filename:
`outbox/{language}_{level}_{story_name}_pack.pdf`

```bash
mkdir -p outbox
venv/bin/python tools/pack.py \
  --story-dir {story_dir} \
  --vocab-pdf temp/vocab_sheet.pdf \
  --output outbox/{language}_{level}_{story_name}_pack.pdf
```

### Step 5 — Clean up and report

```bash
rm temp/vocab_sheet.pdf
```

Report to the user:
- Full output path
- Total page count (printed by `pack.py`)
- The `word_count` vocabulary words selected, with a one-sentence rationale
  (e.g. "These 5 words carry the core plot and sit at the teachable gap for HSK2.")

## Notes

- Always use `venv/bin/python` to invoke tools.
- Merge order is fixed: story → vocabulary sheet → study copy → questions.
- The vocabulary sheet is always 2 pages (40 rows). Pre-populated rows come
  first; the rest are blank for the student to fill in during or after reading.
- Use the pinyin exactly as written in the vocabulary table — do not re-derive it.
- The `|` separator in `--words` is unambiguous: pipe never appears in hanzi or
  pinyin, so it does not need quoting within the value.
