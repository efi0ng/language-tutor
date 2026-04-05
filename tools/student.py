#!/usr/bin/env python3
"""Student progress management tool.

Usage:
    # Create a new student profile
    venv/bin/python tools/student.py init efi0ng --level 1

    # Mark a material as completed (also updates vocabulary.json)
    venv/bin/python tools/student.py complete efi0ng \\
        --path materials/chinese/stories/HSK1/the_painter \\
        --modalities read listened

    # Add a modality to an already-completed material
    venv/bin/python tools/student.py add-modality efi0ng \\
        --path materials/chinese/stories/HSK1/the_painter \\
        --modality spoken

    # Show vocabulary coverage and readiness stats
    venv/bin/python tools/student.py stats efi0ng
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import date

logging.getLogger("jieba").setLevel(logging.ERROR)
import jieba

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
STUDENTS_DIR = os.path.join(REPO_ROOT, "students")
HSK_CSV = os.path.join(os.path.dirname(__file__), "data", "hsk30.csv")

COVERAGE_THRESHOLD = 0.70   # fraction of current level's vocab that must be seen
MIN_COMPLETIONS = 3          # completed materials at current level with read+listened


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def student_dir(nickname, language):
    return os.path.join(STUDENTS_DIR, nickname, language)


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def require_student(nickname, language):
    path = os.path.join(student_dir(nickname, language), "profile.json")
    if not os.path.exists(path):
        print(f"Error: no profile for '{nickname}/{language}'. Run 'init' first.", file=sys.stderr)
        sys.exit(1)
    return load_json(path, {})


def load_hsk_dict():
    """Return (word→level dict, level→set-of-words dict)."""
    word_level = {}
    words_by_level = {}
    with open(HSK_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            level_str = row["Level"].strip()
            try:
                level = int(level_str)
            except ValueError:
                level = int(level_str.split("-")[0])
            for word in row["Simplified"].split("|"):
                word = word.strip()
                if not word:
                    continue
                if word not in word_level or level < word_level[word]:
                    word_level[word] = level
                words_by_level.setdefault(level, set()).add(word)
    return word_level, words_by_level


def is_cjk(char):
    cp = ord(char)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0xF900 <= cp <= 0xFAFF
        or 0x20000 <= cp <= 0x2A6DF
    )


def extract_body_text(md_path):
    """Return the body text of a story.md or extract.md (strips title and vocab table)."""
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    # Everything before the first --- separator
    body = content.split("\n---\n", 1)[0]
    # Drop the title line
    lines = body.splitlines()
    start = next((i + 1 for i, l in enumerate(lines) if l.startswith("# ")), 0)
    return "\n".join(lines[start:]).strip()


def extract_title(md_path):
    with open(md_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("# "):
                return line[2:].strip()
    return os.path.basename(os.path.dirname(md_path))


def get_material_info(path):
    """Return (type, level, name, title, md_path) for a material path."""
    path = path.rstrip("/")
    name = os.path.basename(path)
    parts = path.replace("\\", "/").split("/")

    if "stories" in parts:
        mat_type = "story"
        level = parts[parts.index("stories") + 1]
        md_path = os.path.join(REPO_ROOT, path, "story.md")
    elif "extracts" in parts:
        mat_type = "extract"
        level = None
        md_path = os.path.join(REPO_ROOT, path, "extract.md")
    else:
        mat_type = "unknown"
        level = None
        md_path = None

    md_path_abs = os.path.normpath(md_path) if md_path else None
    title = extract_title(md_path_abs) if md_path_abs and os.path.exists(md_path_abs) else name
    return mat_type, level, name, title, md_path_abs


def update_vocabulary(nickname, language, text, source_name, word_level):
    """Segment text and merge word frequencies into vocabulary.json."""
    jieba.initialize()
    for word in word_level:
        if len(word) > 1:
            jieba.add_word(word, freq=1000)

    seen = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        for segment in jieba.cut(line):
            if word_level.get(segment) is not None:
                seen.add(segment)
            elif len(segment) > 1:
                for char in segment:
                    if is_cjk(char) and char in word_level:
                        seen.add(char)

    voc_path = os.path.join(student_dir(nickname, language), "vocabulary.json")
    vocab = load_json(voc_path, {})

    for word in seen:
        if word in vocab:
            vocab[word]["seen"] += 1
            if source_name not in vocab[word]["sources"]:
                vocab[word]["sources"].append(source_name)
        else:
            vocab[word] = {
                "seen": 1,
                "hsk_level": word_level[word],
                "sources": [source_name],
            }

    save_json(voc_path, vocab)
    return len(seen)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(args):
    d = student_dir(args.nickname, args.language)
    os.makedirs(d, exist_ok=True)
    profile_path = os.path.join(d, "profile.json")
    if os.path.exists(profile_path) and not args.force:
        print(f"Profile '{args.nickname}/{args.language}' already exists. Use --force to overwrite.")
        return
    save_json(profile_path, {
        "nickname": args.nickname,
        "language": args.language,
        "current_level": args.level,
        "started": str(date.today()),
    })
    save_json(os.path.join(d, "completed.json"), [])
    save_json(os.path.join(d, "vocabulary.json"), {})
    print(f"Created profile '{args.nickname}/{args.language}' at HSK {args.level}.")


def cmd_complete(args):
    require_student(args.nickname, args.language)
    mat_type, level, name, title, md_path = get_material_info(args.path)

    if not md_path or not os.path.exists(md_path):
        print(f"Error: cannot find content file at {md_path}", file=sys.stderr)
        sys.exit(1)

    comp_path = os.path.join(student_dir(args.nickname, args.language), "completed.json")
    completed = load_json(comp_path, [])

    existing = next((e for e in completed if e["path"] == args.path), None)
    if existing:
        merged = sorted(set(existing["modalities"]) | set(args.modalities))
        existing["modalities"] = merged
        print(f"Updated '{title}' — modalities: {merged}")
    else:
        completed.append({
            "path": args.path,
            "title": title,
            "type": mat_type,
            "level": level,
            "date": str(date.today()),
            "modalities": sorted(args.modalities),
        })
        print(f"Marked complete: '{title}' [{mat_type}, {level}] — {sorted(args.modalities)}")

    save_json(comp_path, completed)

    word_level, _ = load_hsk_dict()
    n = update_vocabulary(args.nickname, args.language, extract_body_text(md_path), name, word_level)
    print(f"Vocabulary: {n} unique HSK words seen in this material.")


def cmd_add_modality(args):
    require_student(args.nickname, args.language)
    comp_path = os.path.join(student_dir(args.nickname, args.language), "completed.json")
    completed = load_json(comp_path, [])

    existing = next((e for e in completed if e["path"] == args.path), None)
    if not existing:
        print(f"Error: '{args.path}' not in completed list. Run 'complete' first.", file=sys.stderr)
        sys.exit(1)

    if args.modality not in existing["modalities"]:
        existing["modalities"] = sorted(set(existing["modalities"]) | {args.modality})
        save_json(comp_path, completed)
        print(f"Added '{args.modality}' to '{existing['title']}'.")
    else:
        print(f"'{args.modality}' already recorded for '{existing['title']}'.")


def cmd_stats(args):
    profile = require_student(args.nickname, args.language)
    current_level = int(profile.get("current_level", 1))

    word_level, words_by_level = load_hsk_dict()
    vocab = load_json(os.path.join(student_dir(args.nickname, args.language), "vocabulary.json"), {})
    completed = load_json(os.path.join(student_dir(args.nickname, args.language), "completed.json"), [])
    seen_words = set(vocab.keys())

    print(f"\n=== {args.nickname}  (HSK {current_level}) ===\n")

    print("Vocabulary coverage by level:")
    for lvl in sorted(words_by_level.keys()):
        level_words = words_by_level[lvl]
        seen = len(seen_words & level_words)
        total = len(level_words)
        pct = seen / total * 100 if total else 0
        filled = int(pct / 5)
        bar = "█" * filled + "░" * (20 - filled)
        label = f"HSK {lvl}" if lvl <= 6 else "HSK 7-9"
        print(f"  {label:8s}  {bar}  {seen:4d}/{total:4d}  ({pct:5.1f}%)")

    print(f"\nCompleted materials ({len(completed)} total):")
    by_level = {}
    for e in completed:
        key = e.get("level") or "extract"
        by_level.setdefault(key, []).append(e)
    for key in sorted(by_level.keys()):
        print(f"  {key}:")
        for e in by_level[key]:
            mods = ", ".join(e.get("modalities", []))
            print(f"    • {e['title']}  [{mods}]  {e.get('date', '')}")

    # Readiness
    level_words = words_by_level.get(current_level, set())
    if level_words:
        coverage = len(seen_words & level_words) / len(level_words)
        qualifying = [
            e for e in completed
            if e.get("level") == f"HSK{current_level}"
            and {"read", "listened"}.issubset(set(e.get("modalities", [])))
        ]
        ready = coverage >= COVERAGE_THRESHOLD and len(qualifying) >= MIN_COMPLETIONS
        print(f"\nReadiness for HSK {current_level + 1}:")
        cov_ok = "✓" if coverage >= COVERAGE_THRESHOLD else "✗"
        comp_ok = "✓" if len(qualifying) >= MIN_COMPLETIONS else "✗"
        print(f"  {cov_ok} Vocabulary coverage of HSK {current_level}: "
              f"{coverage*100:.1f}% (threshold: {COVERAGE_THRESHOLD*100:.0f}%)")
        print(f"  {comp_ok} Materials at HSK {current_level} with read+listened: "
              f"{len(qualifying)} (threshold: {MIN_COMPLETIONS})")
        print(f"  {'→ Ready to progress!' if ready else '→ Keep going.'}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Student progress management")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Create a new student profile")
    p.add_argument("nickname")
    p.add_argument("--language", required=True, help="Language being studied (e.g. chinese, english)")
    p.add_argument("--level", type=int, default=1, help="Starting HSK level (default: 1)")
    p.add_argument("--force", action="store_true", help="Overwrite existing profile")

    p = sub.add_parser("complete", help="Mark a material as completed")
    p.add_argument("nickname")
    p.add_argument("--language", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--modalities", nargs="+", required=True,
                   choices=["read", "listened", "spoken"])

    p = sub.add_parser("add-modality", help="Add a modality to a completed material")
    p.add_argument("nickname")
    p.add_argument("--language", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--modality", required=True, choices=["read", "listened", "spoken"])

    p = sub.add_parser("stats", help="Show progress and readiness")
    p.add_argument("nickname")
    p.add_argument("--language", required=True)

    args = parser.parse_args()
    {"init": cmd_init, "complete": cmd_complete,
     "add-modality": cmd_add_modality, "stats": cmd_stats}[args.command](args)


if __name__ == "__main__":
    main()
