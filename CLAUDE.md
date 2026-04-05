# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Language Tutor is a Claude Code environment for:
- Generating language learning materials (stories, extracts) with audio and study PDFs
- Tracking student progress through completed materials
- Running adaptive HSK vocabulary assessments

## Project Structure

```
materials/{language}/stories/{level}/{story_name}/   # Generated stories, audio, PDFs
materials/{language}/extracts/{extract_name}/        # Real-world text extracts
students/{nickname}/{language}/                      # Per-student progress data (gitignored assessments)
  profile.json                                       # Current level, start date
  completed.json                                     # Completed materials + modalities
  vocabulary.json                                    # Word frequency from studied materials
temp/                                                # Temporary files (cleaned up after each skill run)
tools/                                               # Python utilities
tools/data/                                          # hsk30.csv, cedict_hsk.json
.claude/skills/                                      # Claude Code skill definitions
```

## Students

| Nickname | Language | Notes |
|---|---|---|
| efi0ng | chinese | The user (me) |
| mulata | english | The user's wife |

## Python Environment

A virtual environment is at `venv/`. Run Python tools via:
```
venv/bin/python tools/tts.py ...
```

## Tools

### TTS (`tools/tts.py`)
Text-to-speech using edge-tts. Supports many languages.
```
venv/bin/python tools/tts.py --text "你好" --output out.mp3 --lang zh-CN
venv/bin/python tools/tts.py --file input.txt --output out.mp3 --lang zh-CN
venv/bin/python tools/tts.py --list-voices zh-CN
```
Use `--rate "-15%"` for beginner content, `--rate "-5%"` for intermediate.

### PDF (`tools/pdf.py`)
Generate printable PDFs with large, clear font. Supports CJK via TTF fonts.
```
venv/bin/python tools/pdf.py --text "你好" --output out.pdf --title "Story Title"
venv/bin/python tools/pdf.py --file input.txt --output out.pdf --title "Story Title"
venv/bin/python tools/pdf.py --file input.txt --output out.pdf --font /path/to/font.ttf --font-size 20
```
Default font: `tools/NotoSansSC-Regular.ttf` (Noto Sans SC, TrueType outlines). Default size: 18pt.

For HSK colour-coded study PDFs, use `--mode study --annotations temp/annotations.json`.

### HSK Annotator (`tools/hsk_annotate.py`)
Segments Chinese text and outputs per-character HSK level annotations for colour-coded PDFs.
```
venv/bin/python tools/hsk_annotate.py --file temp/text.txt --reader-level 1 --output temp/annotations.json
```

### Student Progress (`tools/student.py`)
Tracks completed materials, vocabulary, and level readiness per student. Use the `/progress` skill rather than calling this directly.
```
venv/bin/python tools/student.py init {nickname} --language {language}
venv/bin/python tools/student.py complete {nickname} --language {language} --path {path} --modalities read listened
venv/bin/python tools/student.py add-modality {nickname} --language {language} --path {path} --modality spoken
venv/bin/python tools/student.py stats {nickname} --language {language}
```

### HSK Assessment (`tools/assess.py`)
Adaptive two-part vocabulary test (recognition + production) with confirmation round. Runs as a local Flask web server. Requires one-time setup via `build_cedict.py`.
```
venv/bin/python tools/assess.py {nickname} [--language chinese] [--port 5731] [--no-open]
```
Results are saved to `students/{nickname}/{language}/assessments.json` only when the user clicks "Save to profile" on the results page.

### Build CEDICT (`tools/build_cedict.py`)
One-time setup: downloads CC-CEDICT and builds `tools/data/cedict_hsk.json`. Already run; only needed if regenerating.
```
venv/bin/python tools/build_cedict.py
```
