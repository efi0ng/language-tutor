# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Language Tutor is a Claude Code environment for:
- Generating language learning materials and assignments
- Validating student work against assignments

## Project Structure

```
materials/{language}/stories/{level}/{story_name}/   # Generated stories, audio, questions
materials/{language}/                                 # Other language materials (e.g., materials/chinese/)
temp/                                                 # Temporary files (e.g., TTS input text)
tools/                                                # Python utilities (TTS, etc.)
.claude/skills/                                       # Claude Code skill definitions
```

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
