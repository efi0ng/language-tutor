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
- **story_title**: Human-readable title for the vocabulary sheet subtitle. Read
  from the `# Title` heading in `story.md` or infer from the directory name.

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
`## Vocabulary` heading or similar). It has columns:
- Chinese: Word | Pinyin | English
- Latin-script languages: Word | English

Extract **all rows** from the table.

### Step 2 — Build the word list

Build an entry for every vocabulary word in the form `"WORD|PINYIN|TRANSLATION"`.

- For Chinese: use the Word, Pinyin, and English columns directly.
- For Latin-script languages (English, French, Spanish, etc.): set pinyin to
  empty — use the form `"WORD||TRANSLATION"`.

Use pinyin exactly as written in the vocabulary table — do not re-derive it.

### Step 3 — Generate the vocabulary sheet

```bash
venv/bin/python tools/vocab_sheet.py \
  --output temp/vocab_sheet.pdf \
  --title "{story_title}" \
  --words "W1|P1|T1" "W2|P2|T2" ...
```

Pass all words as separate quoted `--words` arguments. The sheet is a compact
reference list (original → translation) in two columns, typically one page.

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

## Notes

- Always use `venv/bin/python` to invoke tools.
- Merge order is fixed: story → vocabulary sheet → study copy → questions.
- The vocabulary sheet is a reference list (no blank rows). All story vocabulary
  is included; it fits on one page for most stories, two pages for very long ones.
- The `|` separator in `--words` is unambiguous: pipe never appears in hanzi or
  pinyin, so it does not need quoting within the value.
