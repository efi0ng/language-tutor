# Story Generation Skill

## Activation

This skill activates when the user asks to create a story for language learning. Look for requests mentioning stories, short stories, reading practice, or narrative generation for language study.

## Inputs (extract from the user's prompt)

- **language**: The target language (e.g. "simplified chinese", "japanese", "french"). Determine from context.
- **language_level**: The proficiency level or vocabulary set to constrain to (e.g. "HSK1", "HSK2", "JLPT N5", "A1", "B1"). This controls vocabulary complexity.
- **word_count**: Approximate target length. Default to ~150 words/characters if not specified.
- **topic** (optional): A theme or subject for the story.
- **story_name**: A short slug derived from the topic or story content (e.g. "the_lost_cat", "morning_market").

## Language mapping

Map the language to these values for file paths and TTS:

| Language | folder name | TTS lang code |
|---|---|---|
| Simplified Chinese | chinese | zh-CN |
| Japanese | japanese | ja-JP |
| Korean | korean | ko-KR |
| French | french | fr-FR |
| German | german | de-DE |
| Spanish | spanish | es-ES |
| Italian | italian | it-IT |
| Portuguese (BR) | portuguese | pt-BR |
| English | english | en-US |
| Russian | russian | ru-RU |
| Thai | thai | th-TH |
| Vietnamese | vietnamese | vi-VN |

For languages not listed, use the language name in lowercase as the folder name and look up the TTS code via:
```
./venv/bin/python ./tools/tts.py --list-voices
```

## Output structure

All files go into: `materials/{language}/stories/{language_level}/{story_name}/`

Any temporary files go under the `temp/` folder.

Create these six files:

### 1. `story.md` — The story text

Write a markdown file with this structure:

```markdown
# {Story Title in target language}

{story text in the target language}

---

## Vocabulary

| Word | Pinyin/Reading | English |
|---|---|---|
| ... | ... | ... |

```

The vocabulary table should list key words used in the story. Include romanization/reading aids appropriate to the language (pinyin for Chinese, furigana-style for Japanese, romanization for Korean, etc.). For languages using Latin script, omit the reading column.

### 2. `narration.mp3` — Audio narration

Generate using the TTS tool. Only narrate the story text itself (not the title, vocabulary, or questions).

Extract the plain story text (no markdown formatting) and run:
```bash
/home/efi0ng/src/language_tutor/venv/bin/python /home/efi0ng/src/language_tutor/tools/tts.py \
  --file temp/story_text.txt \
  --output materials/{language}/stories/{language_level}/{story_name}/narration.mp3 \
  --lang {tts_lang_code} \
  --rate="-15%"
```

IMPORTANT: Always use `--rate="value"` with `=` (not a space) because the leading `-` in rates like `-15%` confuses argparse.

Use `--rate="-15%"` for beginner levels (HSK1-2, JLPT N5-N4, A1-A2) to slow down speech. Use `--rate="-5%"` for intermediate and `--rate="+0%"` for advanced.

If the story text is long or contains special characters that may cause shell quoting issues, write the plain text to a temporary file and use `--file` instead of `--text`.

### 3. `questions.md` — Comprehension questions

Write 3-5 comprehension questions **in the target language**, using vocabulary at or below the specified level. Structure:

```markdown
# {Comprehension Questions title in target language}

1. {question}
2. {question}
3. {question}
```


### 4. `answerkey.md` - Answer Key

Write the answer key **in the target language** to the questions we wrote to questions.md, using vocabulary at or below the specified level. Structure:

```markdown
# {Comprehension Answer Key title in target language}

1. {answer}
2. {answer}
3. {answer}
```

### 5. `translation.md` — English translation

Write a paragraph-by-paragraph English translation of the story. Structure:

```markdown
# {Story Title translated to English}

{English translation of the story, preserving the same paragraph breaks as the original}
```

### 6. `story.pdf` — Printable story

Generate a printable PDF of the story using the PDF tool. Use the plain story text (same as for narration) and the story title.

```bash
/home/efi0ng/src/language_tutor/venv/bin/python /home/efi0ng/src/language_tutor/tools/pdf.py \
  --file temp/story_text.txt \
  --title "{Story Title}" \
  --output materials/{language}/stories/{language_level}/{story_name}/story.pdf
```

## Story writing guidelines

- **Strictly constrain vocabulary** to the specified level. For Chinese HSK levels, use primarily words from that HSK list. Occasional words one level above are acceptable if meaning is clear from context, but flag them in the vocabulary table.
- Write natural, engaging stories — not textbook exercises. Use simple plot structures: a problem and resolution, a daily routine, a short encounter.
- For Chinese: use simplified characters only. Include natural dialogue where appropriate.
- Target the requested word/character count approximately (±20% is fine).
- The story should be self-contained and have a clear beginning, middle, and end.

## Procedure

1. Determine the language, level, word count, and topic from the user's request.
2. Create the output directory: `mkdir -p materials/{language}/stories/{language_level}/{story_name}`
3. Write the story content to `story.md`.
4. Write the comprehension questions to `questions.md`.
5. Write the comprehension question answer key to `answerkey.md`.
6. Write the English translation to `translation.md`.
7. Write the plain story text (no markdown) to a temp file, then generate `narration.mp3` using the TTS tool.
8. Generate `story.pdf` using the PDF tool with the same temp file and the story title.
9. Clean up the temp file.
10. Report to the user what was created, including the file paths.
