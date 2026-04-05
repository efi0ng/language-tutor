#!/usr/bin/env python3
"""HSK Vocabulary Assessment Server.

Two-part adaptive test: recognition (Chinese → English) then production
(English → Chinese). Automatically stops when enough statistical evidence
is collected. Runs as a local Flask web server.

Usage:
    venv/bin/python tools/assess.py efi0ng [--language chinese] [--port 5731] [--no-open]

Prerequisites:
    venv/bin/pip install flask
    venv/bin/python tools/build_cedict.py   # one-time setup
"""

import argparse
import asyncio
import io
import json
import os
import random
import sys
import threading
import time
import uuid
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request, send_file

import assess_data

# ---------------------------------------------------------------------------
# Constants (tunable)
# ---------------------------------------------------------------------------

MAX_WORDS         = 20   # max words per level in recognition + production
MIN_FOR_PASS      = 10   # min words before an early-pass decision
PASS_THRESHOLD    = 0.75
EXTENDED_COUNT    = 30   # confirmation round word count

# ---------------------------------------------------------------------------
# Adaptive algorithm helpers
# ---------------------------------------------------------------------------

def check_level_status(n: int, c: int, max_words: int = MAX_WORDS) -> str:
    """Return "ongoing", "passed", or "failed" after n attempts with c correct."""
    if n == 0:
        return "ongoing"
    remaining = max_words - n
    if (c + remaining) / max_words < PASS_THRESHOLD:
        return "failed"
    if n >= MIN_FOR_PASS and c / n >= PASS_THRESHOLD:
        return "passed"
    if n >= max_words:
        return "passed" if c / n >= PASS_THRESHOLD else "failed"
    return "ongoing"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

@dataclass
class LevelResult:
    level: int
    phase: str          # "recognition" | "production" | "confirmation"
    words: list = field(default_factory=list)      # words in order
    correct: list = field(default_factory=list)    # bool per word
    answers: list = field(default_factory=list)    # raw answers (production)
    status: str = "ongoing"                        # "ongoing"|"passed"|"failed"

    def n(self): return len(self.words)
    def c(self): return sum(self.correct)
    def score(self): return self.c() / self.n() if self.n() else 0.0


class AssessmentSession:
    def __init__(self, nickname: str, language: str, current_level: int,
                 cedict: dict, words_by_level: dict):
        self.session_id = str(uuid.uuid4())
        self.nickname = nickname
        self.language = language
        self.created_at = time.time()
        self.saved = False

        self.cedict = cedict
        self.words_by_level = words_by_level

        self.rng = random.Random()  # unseeded = different each run

        self.current_level_val = current_level
        self.start_level = max(1, current_level - 1)

        # Phase: "recognition" → "production" → "confirmation" → "done"
        self.phase = "recognition"
        self.current_level = self.start_level

        # Pre-sample recognition words for all levels at session start
        self.recognition_samples: dict = {}    # level → [word, ...]
        self.production_samples: dict = {}     # level → [word, ...]
        self.confirmation_sample: list = []    # words for the confirmation round

        all_levels = sorted(words_by_level.keys())
        sampled_so_far: dict = {lvl: set() for lvl in all_levels}
        for lvl in all_levels:
            if lvl >= self.start_level:
                sample = assess_data.sample_words(
                    lvl, MAX_WORDS, set(), self.rng, words_by_level, cedict
                )
                self.recognition_samples[lvl] = sample
                sampled_so_far[lvl].update(sample)

        self.results: list = []                    # completed LevelResults
        self.current_result: LevelResult = LevelResult(
            level=self.current_level, phase="recognition"
        )
        self._current_word: str = ""
        self._correct_key: str = ""
        self._choices: list = []

    # ------------------------------------------------------------------
    # Levels that passed recognition (used to scope production)
    # ------------------------------------------------------------------

    def _recognition_passed_levels(self) -> list:
        return sorted(
            r.level for r in self.results
            if r.phase == "recognition" and r.status == "passed"
        )

    def _determined_level(self) -> int:
        """Highest level where both recognition and production passed."""
        prod_passed = {
            r.level for r in self.results
            if r.phase == "production" and r.status == "passed"
        }
        rec_passed = {
            r.level for r in self.results
            if r.phase == "recognition" and r.status == "passed"
        }
        both = rec_passed & prod_passed
        # Also count levels where recognition passed but no production yet
        # (handled after confirmation)
        return max(both) if both else 0

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def _finish_current_level(self):
        """Finalise the current LevelResult and advance to the next state."""
        self.results.append(self.current_result)
        res = self.current_result
        phase = res.phase

        if phase == "recognition":
            if res.status == "passed":
                next_level = res.level + 1
                if next_level in self.recognition_samples:
                    self.current_level = next_level
                    self.current_result = LevelResult(
                        level=next_level, phase="recognition"
                    )
                else:
                    # Reached max level — start production
                    self._start_production()
            else:
                # Recognition failed — start production on passed levels
                self._start_production()

        elif phase == "production":
            passed_levels = self._recognition_passed_levels()
            current_idx = passed_levels.index(res.level) if res.level in passed_levels else -1
            next_idx = current_idx + 1
            if next_idx < len(passed_levels):
                next_lvl = passed_levels[next_idx]
                self.current_level = next_lvl
                self.current_result = LevelResult(level=next_lvl, phase="production")
            else:
                # Production done — start confirmation
                self._start_confirmation()

        elif phase == "confirmation":
            self.phase = "done"

    def _start_production(self):
        self.phase = "production"
        passed = self._recognition_passed_levels()
        if not passed:
            self._start_confirmation()
            return
        # Sample production words (fresh, no overlap with recognition words)
        for lvl in passed:
            used = set(self.recognition_samples.get(lvl, []))
            sample = assess_data.sample_words(
                lvl, MAX_WORDS, used, self.rng, self.words_by_level, self.cedict
            )
            self.production_samples[lvl] = sample
        self.current_level = passed[0]
        self.current_result = LevelResult(level=passed[0], phase="production")

    def _start_confirmation(self):
        self.phase = "confirmation"
        det = self._determined_level()
        if det == 0:
            # Nothing passed — no confirmation needed
            self.phase = "done"
            return
        # Sample confirmation words: fresh, no overlap with recognition or production
        used = set(self.recognition_samples.get(det, []))
        used |= set(self.production_samples.get(det, []))
        sample = assess_data.sample_words(
            det, EXTENDED_COUNT, used, self.rng, self.words_by_level, self.cedict
        )
        self.confirmation_sample = sample
        self.current_level = det
        self.current_result = LevelResult(level=det, phase="confirmation")

    # ------------------------------------------------------------------
    # Next question
    # ------------------------------------------------------------------

    def next_question(self) -> dict:
        """Prepare the next question and return the response dict for /api/next."""
        if self.phase == "done":
            return {"phase": "done"}

        cr = self.current_result
        phase = cr.phase

        # Pick next word from the appropriate sample
        if phase == "recognition":
            sample = self.recognition_samples.get(cr.level, [])
        elif phase == "production":
            sample = self.production_samples.get(cr.level, [])
        else:  # confirmation
            sample = self.confirmation_sample

        word_idx = cr.n()
        if word_idx >= len(sample):
            # Should not happen normally; treat as done
            return {"phase": "done"}

        word = sample[word_idx]
        self._current_word = word
        entry = self.cedict[word]

        total = len(sample)

        if phase in ("recognition", "confirmation"):
            choices, correct_key = assess_data.build_choices(
                word, cr.level, self.cedict, self.rng
            )
            self._choices = choices
            self._correct_key = correct_key
            return {
                "phase": phase,
                "level": cr.level,
                "question_number": word_idx + 1,
                "total_in_level": total,
                "word": word,
                "pinyin": entry.get("pinyin", ""),
                "choices": choices,
            }
        else:  # production
            self._correct_key = word  # graded differently
            return {
                "phase": "production",
                "level": cr.level,
                "question_number": word_idx + 1,
                "total_in_level": total,
                "prompt": assess_data._first_short_def(entry.get("definitions", []), max_len=150),
                "pos": entry.get("pos", ""),
                "pinyin_hint": entry.get("pinyin", ""),
            }

    # ------------------------------------------------------------------
    # Record answer
    # ------------------------------------------------------------------

    def record_answer(self, answer: str) -> dict:
        """Record student's answer. Return {correct, correct_answer, level_status, stats}."""
        cr = self.current_result
        word = self._current_word
        entry = self.cedict.get(word, {})

        if cr.phase in ("recognition", "confirmation"):
            is_correct = (answer.upper() == self._correct_key)
            correct_answer = next(
                (c["text"] for c in self._choices if c["key"] == self._correct_key), ""
            )
        else:
            is_correct = assess_data.grade_production(answer, entry)
            correct_answer = entry.get("simplified", word)

        cr.words.append(word)
        cr.correct.append(is_correct)
        if cr.phase == "production":
            cr.answers.append(answer)

        max_w = EXTENDED_COUNT if cr.phase == "confirmation" else MAX_WORDS
        cr.status = check_level_status(cr.n(), cr.c(), max_w)

        if cr.status != "ongoing":
            self._finish_current_level()

        return {
            "correct": is_correct,
            "correct_answer": correct_answer,
            "level_status": cr.status,
            "stats": {"correct": cr.c(), "attempted": cr.n()},
        }

    # ------------------------------------------------------------------
    # Final results
    # ------------------------------------------------------------------

    def build_results(self) -> dict:
        recognition = {}
        production = {}
        confirmation = None

        for r in self.results:
            data = {
                "score": round(r.score(), 3),
                "questions": r.n(),
                "passed": r.status == "passed",
                "words_tested": r.words,
                "correct": r.correct,
            }
            if r.phase == "recognition":
                recognition[str(r.level)] = data
            elif r.phase == "production":
                data["answers_given"] = r.answers
                production[str(r.level)] = data
            elif r.phase == "confirmation":
                confirmation = data
                confirmation["level"] = r.level

        det = self._determined_level()

        # recognition_ceiling = first level where recognition failed
        rec_ceiling = None
        for r in sorted(self.results, key=lambda x: x.level):
            if r.phase == "recognition" and r.status == "failed":
                rec_ceiling = r.level
                break

        return {
            "id": self.session_id,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "nickname": self.nickname,
            "language": self.language,
            "recognition": recognition,
            "production": production,
            "confirmation": confirmation,
            "determined_level": det,
            "previous_level": self.current_level_val,
            "recognition_ceiling": rec_ceiling,
        }


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

SESSIONS: dict = {}

REPO_ROOT    = os.path.join(os.path.dirname(__file__), "..")
STUDENTS_DIR = os.path.join(REPO_ROOT, "students")

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))

# Globals set at startup
_NICKNAME: str = ""
_LANGUAGE: str = "chinese"
_CURRENT_LEVEL: int = 1
_CEDICT: dict = {}
_WORDS_BY_LEVEL: dict = {}


@app.route("/")
def index():
    return render_template(
        "assess.html",
        nickname=_NICKNAME,
        current_level=_CURRENT_LEVEL,
    )


@app.route("/api/start", methods=["POST"])
def api_start():
    session = AssessmentSession(
        nickname=_NICKNAME,
        language=_LANGUAGE,
        current_level=_CURRENT_LEVEL,
        cedict=_CEDICT,
        words_by_level=_WORDS_BY_LEVEL,
    )
    SESSIONS[session.session_id] = session
    return jsonify({
        "session_id": session.session_id,
        "start_level": session.start_level,
        "current_level": _CURRENT_LEVEL,
    })


@app.route("/api/next")
def api_next():
    sid = request.args.get("session_id")
    session = SESSIONS.get(sid)
    if not session:
        return jsonify({"error": "session not found"}), 404
    return jsonify(session.next_question())


@app.route("/api/answer", methods=["POST"])
def api_answer():
    data = request.get_json()
    sid = data.get("session_id")
    session = SESSIONS.get(sid)
    if not session:
        return jsonify({"error": "session not found"}), 404
    answer = data.get("answer", "")
    result = session.record_answer(answer)
    return jsonify(result)


@app.route("/api/results")
def api_results():
    sid = request.args.get("session_id")
    session = SESSIONS.get(sid)
    if not session:
        return jsonify({"error": "session not found"}), 404
    results = session.build_results()
    return jsonify(results)


@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.get_json()
    sid = data.get("session_id")
    session = SESSIONS.get(sid)
    if not session:
        return jsonify({"error": "session not found"}), 404
    if not session.saved:
        results = session.build_results()
        assess_data.save_assessment(_NICKNAME, _LANGUAGE, results)
        session.saved = True
    return jsonify({"saved": True})


@app.route("/api/tts")
def api_tts():
    word = request.args.get("word", "")
    if not word:
        return "", 204
    try:
        import edge_tts
        buf = io.BytesIO()

        async def _synth():
            communicate = edge_tts.Communicate(word, "zh-CN-XiaoxiaoNeural")
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])

        asyncio.run(_synth())
        buf.seek(0)
        return send_file(buf, mimetype="audio/mpeg")
    except Exception:
        return "", 204


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global _NICKNAME, _LANGUAGE, _CURRENT_LEVEL, _CEDICT, _WORDS_BY_LEVEL

    parser = argparse.ArgumentParser(description="HSK vocabulary assessment server")
    parser.add_argument("nickname", help="Student nickname (e.g. efi0ng)")
    parser.add_argument("--language", default="chinese", help="Language being studied (default: chinese)")
    parser.add_argument("--port", type=int, default=5731, help="Port to listen on (default: 5731)")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    _NICKNAME = args.nickname
    _LANGUAGE = args.language

    # Validate student profile
    profile_path = os.path.normpath(
        os.path.join(STUDENTS_DIR, _NICKNAME, _LANGUAGE, "profile.json")
    )
    if not os.path.exists(profile_path):
        print(f"Error: no profile found at {profile_path}", file=sys.stderr)
        print(f"Run:  venv/bin/python tools/student.py init {_NICKNAME} --language {_LANGUAGE}", file=sys.stderr)
        sys.exit(1)
    with open(profile_path) as f:
        profile = json.load(f)
    _CURRENT_LEVEL = int(profile.get("current_level", 1))

    # Load data (exits with helpful message if cedict_hsk.json is missing)
    try:
        _CEDICT = assess_data.load_cedict()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    _WORDS_BY_LEVEL = assess_data.load_hsk_words_by_level(_CEDICT)

    print(f"HSK Assessment  ·  {_NICKNAME}  ·  {_LANGUAGE}  ·  current level: HSK {_CURRENT_LEVEL}")
    total_words = sum(len(v) for v in _WORDS_BY_LEVEL.values())
    print(f"Vocabulary loaded: {total_words:,} testable words across {len(_WORDS_BY_LEVEL)} levels")
    print(f"Starting server on http://localhost:{args.port}/")

    if not args.no_open:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{args.port}/")).start()

    app.run(host="127.0.0.1", port=args.port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
