# Extract Study Skill

## Activation

This skill activates when the user provides Chinese text from an external source (news, articles, social media, etc.) and wants to create study materials from it. Look for requests mentioning real-world text, online sources, news articles, extracts, or "text I found".

## Inputs (extract from the user's prompt or conversation)

- **text**: The raw Chinese text to study (provided by the user)
- **extract_name**: A short slug for the output folder (derive from content if not given, e.g. `qingming_rail_2026`)
- **title**: A human-readable title for the PDF and files (derive from content if not given)
- **reader_level**: The learner's HSK level (default: 1). Used for vocabulary colour-coding.

## Output structure

All files go into: `materials/chinese/extracts/{extract_name}/`

Temporary files go under `temp/`.

Create these files:

### 1. `extract.md` — Source text + vocabulary list

```markdown
# {Title}

{The original Chinese text, verbatim}

---

## 生词表 (Vocabulary above HSK {reader_level})

| Word | Pinyin | English | HSK Level |
|---|---|---|---|
| ... | ... | ... | ... |
```

List **only** words above the reader's level. Group rows by HSK level (ascending). Include proper nouns and technical terms. For HSK 7–9 words, write "HSK 7–9" in the level column.

### 2. `translation.md` — English translation

```markdown
# {Title — English}

{English translation of the text, preserving paragraph breaks}
```

### 3. `narration.mp3` — Audio narration

Same approach as the story skill. Use `--rate="-15%"` for HSK1–2 reader levels, `--rate="-5%"` for HSK3–4, `--rate="+0%"` for HSK5+.

**a.** Write the title to `temp/title_text.txt`, generate title audio:
```bash
venv/bin/python tools/tts.py \
  --file temp/title_text.txt \
  --output temp/title.mp3 \
  --lang zh-CN \
  --rate="-15%"
```

**b.** Write the plain Chinese body text (no markdown) to `temp/extract_text.txt`, generate body audio:
```bash
venv/bin/python tools/tts.py \
  --file temp/extract_text.txt \
  --output temp/extract_narration.mp3 \
  --lang zh-CN \
  --rate="-15%"
```

**c.** Concatenate with a 1-second silence between title and body:
```bash
ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t 1 -acodec libmp3lame -ab 128k temp/silence.mp3

printf "file '$(pwd)/temp/title.mp3'\nfile '$(pwd)/temp/silence.mp3'\nfile '$(pwd)/temp/extract_narration.mp3'\n" > temp/concat_list.txt

ffmpeg -y -f concat -safe 0 -i temp/concat_list.txt \
  -acodec libmp3lame -ab 128k \
  materials/chinese/extracts/{extract_name}/narration.mp3
```

### 4. `extract_study.pdf` — Colour-coded study PDF

This is a CJK character grid where vocabulary above the reader's level is colour-coded:

| Level relative to reader | Colour |
|---|---|
| At or below reader level | Black |
| 1 level above | Dark blue |
| 2 levels above | Dark purple |
| 3+ levels above | Dark red |

**Step 1** — Annotate the text with HSK levels:
```bash
venv/bin/python tools/hsk_annotate.py \
  --file temp/extract_text.txt \
  --reader-level {reader_level} \
  --output temp/annotations.json
```

**Step 2** — Generate the colour-coded study PDF:
```bash
venv/bin/python tools/pdf.py \
  --file temp/extract_text.txt \
  --title "{Title}" \
  --mode study \
  --annotations temp/annotations.json \
  --output materials/chinese/extracts/{extract_name}/extract_study.pdf
```

## Procedure

1. Determine `extract_name`, `title`, and `reader_level` from context.
2. Create the output directory:
   ```bash
   mkdir -p materials/chinese/extracts/{extract_name}
   ```
3. Write `extract.md` with the original text and vocabulary table.
4. Write `translation.md` with the English translation.
5. Write the plain Chinese body text (verbatim, no markdown) to `temp/extract_text.txt`.
6. Write the title (plain text) to `temp/title_text.txt`.
7. Generate `narration.mp3` as described above.
8. Run `hsk_annotate.py` to produce `temp/annotations.json`.
9. Generate `extract_study.pdf` using `pdf.py` with the annotations.
10. Clean up temp files: `temp/extract_text.txt`, `temp/title_text.txt`, `temp/title.mp3`, `temp/extract_narration.mp3`, `temp/silence.mp3`, `temp/concat_list.txt`, `temp/annotations.json`.
11. Report what was created, including the file paths.

## Notes

- The vocabulary table in `extract.md` is meant to be a study aid, not an exhaustive list. Include all words above the reader level that appear in the text, but you may group obvious proper nouns (city names, personal names, organisation names) together at the end.
- For the translation, aim for natural, readable English that preserves the tone of the source (formal news → formal English, conversational → conversational).
- The `narration.mp3` enables the extract to be used with the karaoke skill later.
