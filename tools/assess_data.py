#!/usr/bin/env python3
"""Data layer for the HSK assessment tool.

Handles: loading cedict_hsk.json and hsk30.csv, word sampling, distractor
building, production answer grading, and persisting assessment results.
"""

import csv
import json
import os
import random
import re
import unicodedata

# CC-CEDICT entries that are cross-references rather than real English definitions.
# These make terrible answer choices — filter them out.
_META_RE = re.compile(
    r'^(old |archaic |erhua |Japanese )?variant of'
    r'|^see '
    r'|^abbr\. (?:for|of)'
    r'|^surname\b'
    r'|^used in '
    r'|^CJK ',
    re.IGNORECASE
)

CEDICT_JSON = os.path.join(os.path.dirname(__file__), "data", "cedict_hsk.json")
HSK_CSV     = os.path.join(os.path.dirname(__file__), "data", "hsk30.csv")
REPO_ROOT   = os.path.join(os.path.dirname(__file__), "..")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_cedict() -> dict:
    """Load cedict_hsk.json. Raises FileNotFoundError with a helpful message."""
    if not os.path.exists(CEDICT_JSON):
        raise FileNotFoundError(
            f"cedict_hsk.json not found at {CEDICT_JSON}.\n"
            "Run:  venv/bin/python tools/build_cedict.py"
        )
    with open(CEDICT_JSON, encoding="utf-8") as f:
        return json.load(f)


def load_hsk_words_by_level(cedict: dict) -> dict:
    """Return {level_int: [word, ...]} for words that have definitions in cedict."""
    result = {}
    with open(HSK_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            level_str = row["Level"].strip()
            try:
                level = int(level_str)
            except ValueError:
                level = int(level_str.split("-")[0])

            for word in row["Simplified"].split("|"):
                word = word.strip()
                if word and word in cedict and _real_defs(cedict[word]["definitions"]):
                    result.setdefault(level, [])
                    if word not in result[level]:
                        result[level].append(word)

    return result


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def sample_words(level: int, n: int, exclude: set,
                 rng: random.Random,
                 words_by_level: dict, cedict: dict) -> list:
    """Draw up to n words from level, excluding those in `exclude`."""
    pool = [w for w in words_by_level.get(level, []) if w not in exclude]
    return rng.sample(pool, min(n, len(pool)))


# ---------------------------------------------------------------------------
# Recognition: build multiple-choice options
# ---------------------------------------------------------------------------

def _real_defs(defs: list) -> list:
    """Return definitions that are genuine English meanings (not CC-CEDICT meta-references)."""
    return [d for d in defs if not _META_RE.match(d)]


def _first_short_def(defs: list) -> str:
    """Return first real definition, truncated at 60 chars. Falls back to raw first def."""
    real = _real_defs(defs)
    chosen = real[0] if real else (defs[0] if defs else "")
    return chosen[:60]


def build_choices(word: str, level: int, cedict: dict,
                  rng: random.Random) -> tuple:
    """Return (choices, correct_key).

    choices = [{"key": "A", "text": "..."}, ×4] in shuffled order.
    correct_key = "A" / "B" / "C" / "D".
    """
    correct_def = _first_short_def(cedict[word]["definitions"])

    # Gather distractor definitions from adjacent levels
    def_pool = []
    for offset in [0, 1, -1, 2, -2]:
        target_level = level + offset
        for w, entry in cedict.items():
            if entry.get("level") == target_level and w != word:
                d = _first_short_def(_real_defs(entry.get("definitions", [])))
                if d and d != correct_def and d not in def_pool:
                    def_pool.append(d)
        if len(def_pool) >= 30:
            break

    rng.shuffle(def_pool)
    distractors = def_pool[:3]

    # Fill with generic placeholders if somehow short on distractors
    while len(distractors) < 3:
        distractors.append(f"(option {len(distractors)+1})")

    all_defs = [correct_def] + distractors
    rng.shuffle(all_defs)

    keys = ["A", "B", "C", "D"]
    choices = [{"key": keys[i], "text": all_defs[i]} for i in range(4)]
    correct_key = keys[all_defs.index(correct_def)]

    return choices, correct_key


# ---------------------------------------------------------------------------
# Production: grade the student's typed answer
# ---------------------------------------------------------------------------

def _normalise(s: str) -> str:
    """Strip whitespace and normalise Unicode (NFC)."""
    return unicodedata.normalize("NFC", s.strip())


def grade_production(answer: str, word_entry: dict) -> bool:
    """True if answer exactly matches any accepted simplified or traditional form."""
    norm = _normalise(answer)
    accepted = (
        [_normalise(w) for w in word_entry.get("all_simplified", [])]
        + [_normalise(w) for w in word_entry.get("all_traditional", [])]
    )
    return norm in accepted


# ---------------------------------------------------------------------------
# Persisting results
# ---------------------------------------------------------------------------

def save_assessment(nickname: str, language: str, result: dict) -> None:
    """Append result dict to students/{nickname}/{language}/assessments.json atomically."""
    path = os.path.normpath(
        os.path.join(REPO_ROOT, "students", nickname, language, "assessments.json")
    )
    tmp = path + ".tmp"

    existing = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)

    existing.append(result)

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    os.replace(tmp, path)
