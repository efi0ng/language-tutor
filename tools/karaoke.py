#!/usr/bin/env python3
"""
karaoke.py - Generate a karaoke-style video from a language learning story.

The video displays the story text on screen, highlighting each word/character
in sync with the narration audio — like karaoke lyrics.

Supports CJK languages (character-level highlighting) and Latin-script
languages (word-level highlighting).

Usage:
    venv/bin/python tools/karaoke.py \\
        --story materials/chinese/stories/HSK1/surreal_meeting/story.md \\
        --audio materials/chinese/stories/HSK1/surreal_meeting/narration.mp3 \\
        --output materials/chinese/stories/HSK1/surreal_meeting/karaoke.mp4 \\
        --lang zh-CN
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import whisper
from PIL import Image, ImageDraw, ImageFont

# ── Video settings ────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1280, 720
FPS = 24

BG_COLOR       = (15, 18, 28)       # deep navy background
COLOR_PAST     = (80, 85, 100)      # dim gray  – already spoken
COLOR_FUTURE   = (190, 195, 210)    # light gray – not yet spoken
COLOR_CURRENT  = (255, 215, 0)      # gold      – currently spoken
COLOR_TITLE    = (140, 170, 220)    # blue-ish  – title (future state)
COLOR_PROGRESS = (255, 215, 0)      # progress bar

FONT_SIZE       = 54
TITLE_FONT_SIZE = 62
LINE_SPACING    = 1.55
TITLE_POST_GAP  = 50               # extra pixels below title before story text
H_PADDING       = 100
SCROLL_PAD      = 40               # top/bottom padding for the scroll viewport
PROGRESS_H      = 28

FONT_PATH = Path(__file__).parent / "NotoSansSC-Regular.ttf"
SCROLL_EASE = 0.12


# ── Language helpers ──────────────────────────────────────────────────────────

def script_type(lang: str) -> str:
    """Return 'cjk' for character-based scripts, 'latin' for everything else."""
    prefix = lang.lower().split("-")[0]
    return "cjk" if prefix in {"zh", "ja"} else "latin"


def whisper_language(lang: str) -> str:
    """Extract a two-letter ISO 639-1 code from a TTS language tag."""
    return lang.lower().split("-")[0]


# ── Text helpers ──────────────────────────────────────────────────────────────

def extract_narrative(story_path: Path):
    """Return (title, lines) from a story.md, stripping the vocabulary section."""
    text = story_path.read_text(encoding="utf-8")
    title_m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else ""
    body = text.split("---")[0]
    lines = [l.strip() for l in body.splitlines()
             if l.strip() and not l.strip().startswith("#")]
    return title, lines


def wrap_line(line: str, font, max_width: int, draw, stype: str) -> list[str]:
    """Wrap a line to fit max_width. CJK breaks anywhere; Latin breaks on spaces."""
    if stype == "latin":
        segments, current = [], ""
        for word in line.split():
            trial = (current + " " + word).strip()
            if draw.textbbox((0, 0), trial, font=font)[2] > max_width and current:
                segments.append(current)
                current = word
            else:
                current = trial
        if current:
            segments.append(current)
        return segments
    else:
        segments, current = [], ""
        for ch in line:
            trial = current + ch
            if draw.textbbox((0, 0), trial, font=font)[2] > max_width and current:
                segments.append(current)
                current = ch
            else:
                current = trial
        if current:
            segments.append(current)
        return segments


def compute_layout(all_lines, font, title_font, draw_ref, stype):
    """
    Compute scroll layout for all lines (title at index 0, story body after).

    Returns a list of segment dicts:
        { li, seg, offset, y_abs, seg_font, fh }

    `offset` is the character offset of the segment within the original line,
    so that ci_orig = offset + ci_local maps correctly to token char positions.
    """
    available_w = WIDTH - 2 * H_PADDING
    body_fh  = draw_ref.textbbox((0, 0), "字A", font=font)[3]
    title_fh = draw_ref.textbbox((0, 0), "字A", font=title_font)[3]

    items = []
    y = 0
    for li, line in enumerate(all_lines):
        is_title = (li == 0)
        seg_font = title_font if is_title else font
        fh       = title_fh  if is_title else body_fh
        lh       = int(fh * LINE_SPACING)

        segs = wrap_line(line, seg_font, available_w, draw_ref, stype)
        search_start = 0
        for seg_i, seg in enumerate(segs):
            # Find the true character offset of this segment in the original line
            offset = line.find(seg, search_start)
            if offset == -1:
                offset = search_start
            items.append(dict(li=li, seg=seg, offset=offset,
                              y_abs=y, seg_font=seg_font, fh=fh))
            search_start = offset + len(seg)
            y += lh
            if is_title and seg_i == len(segs) - 1:
                y += TITLE_POST_GAP

    return items


# ── Audio helpers ─────────────────────────────────────────────────────────────

def audio_duration(audio_path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", str(audio_path)],
        text=True,
    )
    return float(json.loads(out)["format"]["duration"])


def transcribe(audio_path: Path, model_name: str, lang: str):
    """Return a flat list of {text, start, end} dicts from Whisper."""
    print(f"  Loading Whisper '{model_name}' model…")
    model = whisper.load_model(model_name)
    print("  Transcribing…")
    result = model.transcribe(
        str(audio_path),
        language=whisper_language(lang),
        word_timestamps=True,
        verbose=False,
    )
    words = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            t = w["word"].strip()
            if t:
                words.append({"text": t, "start": w["start"], "end": w["end"]})
    return words


# ── Timeline builders ─────────────────────────────────────────────────────────

def _is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"

def _is_notable_cjk(ch: str) -> bool:
    return _is_cjk(ch) or ch in "，。！？：""''（）、「」…—"

def _clean_latin(w: str) -> str:
    return re.sub(r"[^\w]", "", w.lower())


def build_timeline(all_lines: list[str], whisper_words: list[dict], stype: str):
    """
    Build a flat list of token dicts, each with:
        { line_idx, char_start, char_end, start, end }

    CJK: one token per notable character.
    Latin: one token per word.
    """
    if stype == "cjk":
        return _build_timeline_cjk(all_lines, whisper_words)
    else:
        return _build_timeline_latin(all_lines, whisper_words)


def _build_timeline_cjk(all_lines, whisper_words):
    # Flatten to (char, li, ci, global_idx)
    flat = []
    for li, line in enumerate(all_lines):
        for ci, ch in enumerate(line):
            flat.append((ch, li, ci, len(flat)))

    # Per-char timestamps from Whisper words
    wh_chars = []
    for w in whisper_words:
        zh_in_w = [c for c in w["text"] if _is_cjk(c)]
        n = len(zh_in_w)
        if n == 0:
            continue
        dur = w["end"] - w["start"]
        for i, c in enumerate(zh_in_w):
            wh_chars.append((c,
                             w["start"] + dur * i / n,
                             w["start"] + dur * (i + 1) / n))

    our_zh = [(ch, li, ci, gi) for ch, li, ci, gi in flat if _is_cjk(ch)]
    wi = 0
    zh_times = {}
    for ch, li, ci, gi in our_zh:
        if wi >= len(wh_chars):
            last = list(zh_times.values())[-1] if zh_times else (0, 0)
            zh_times[gi] = (last[1], last[1] + 0.25)
            continue
        matched = False
        for ahead in range(min(6, len(wh_chars) - wi)):
            if wh_chars[wi + ahead][0] == ch:
                _, t0, t1 = wh_chars[wi + ahead]
                zh_times[gi] = (t0, t1)
                wi = wi + ahead + 1
                matched = True
                break
        if not matched:
            _, t0, t1 = wh_chars[wi]
            zh_times[gi] = (t0, t1)
            wi += 1

    tokens = []
    last_end = 0.0
    for ch, li, ci, gi in flat:
        if not _is_notable_cjk(ch):
            continue
        if gi in zh_times:
            t0, t1 = zh_times[gi]
            last_end = t1
        else:
            t0, t1 = last_end, last_end + 0.05
        tokens.append(dict(line_idx=li, char_start=ci, char_end=ci + 1,
                           start=t0, end=t1))
    return tokens


def _build_timeline_latin(all_lines, whisper_words):
    # Collect words with their positions in each line
    text_words = []
    for li, line in enumerate(all_lines):
        for m in re.finditer(r"\S+", line):
            text_words.append(dict(line_idx=li,
                                   char_start=m.start(), char_end=m.end(),
                                   word=m.group()))

    wi = 0
    tokens = []
    last_end = 0.0
    for tw in text_words:
        if wi >= len(whisper_words):
            tokens.append(dict(line_idx=tw["line_idx"],
                               char_start=tw["char_start"],
                               char_end=tw["char_end"],
                               start=last_end, end=last_end + 0.3))
            last_end += 0.3
            continue
        matched = False
        for ahead in range(min(8, len(whisper_words) - wi)):
            if _clean_latin(whisper_words[wi + ahead]["text"]) == _clean_latin(tw["word"]):
                w = whisper_words[wi + ahead]
                tokens.append(dict(line_idx=tw["line_idx"],
                                   char_start=tw["char_start"],
                                   char_end=tw["char_end"],
                                   start=w["start"], end=w["end"]))
                last_end = w["end"]
                wi = wi + ahead + 1
                matched = True
                break
        if not matched:
            w = whisper_words[wi]
            tokens.append(dict(line_idx=tw["line_idx"],
                               char_start=tw["char_start"],
                               char_end=tw["char_end"],
                               start=w["start"], end=w["end"]))
            last_end = w["end"]
            wi += 1

    return tokens


def active_token_index(tokens, t: float) -> int:
    """Return index of the last token whose start ≤ t, or -1."""
    idx = -1
    for i, tok in enumerate(tokens):
        if tok["start"] <= t:
            idx = i
    return idx


# ── Frame renderer ────────────────────────────────────────────────────────────

def char_status(tokens, current_idx: int) -> dict:
    """Map (line_idx, char_idx) → 'past' | 'current' | 'future'."""
    s = {}
    for i, tok in enumerate(tokens):
        li = tok["line_idx"]
        status = "past" if i < current_idx else "current" if i == current_idx else "future"
        for ci in range(tok["char_start"], tok["char_end"]):
            s[(li, ci)] = status
    return s


def render_frame(all_lines, tokens, current_idx, t, font, title_font, layout, camera_y):
    img  = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    viewport_top    = SCROLL_PAD
    viewport_bottom = HEIGHT - PROGRESS_H
    viewport_h      = viewport_bottom - viewport_top

    statuses = char_status(tokens, current_idx)

    for item in layout:
        li, seg, offset = item["li"], item["seg"], item["offset"]
        seg_font = item["seg_font"]
        fh = item["fh"]

        y_screen = viewport_top + item["y_abs"] - camera_y
        if y_screen + fh < viewport_top or y_screen > viewport_bottom:
            continue

        # Pass 1 — measure char x-positions
        seg_w = sum(draw.textbbox((0, 0), c, font=seg_font)[2] for c in seg)
        x = (WIDTH - seg_w) // 2
        char_data = []   # (ch, x, cw, ci_orig, status)
        for ci_local, ch in enumerate(seg):
            cw     = draw.textbbox((0, 0), ch, font=seg_font)[2]
            ci_orig = offset + ci_local
            st     = statuses.get((li, ci_orig), "future")
            char_data.append((ch, x, cw, ci_orig, st))
            x += cw

        # Pass 2 — draw one highlight background per contiguous "current" run
        in_run, run_x0, run_x1 = False, 0, 0
        for ch, cx, cw, _, st in char_data:
            if st == "current":
                if not in_run:
                    in_run, run_x0 = True, cx
                run_x1 = cx + cw
            elif in_run:
                pad = 4
                draw.rounded_rectangle(
                    [run_x0 - pad, y_screen - pad,
                     run_x1 + pad, y_screen + fh + pad],
                    radius=6, fill=(60, 50, 10)
                )
                in_run = False
        if in_run:
            pad = 4
            draw.rounded_rectangle(
                [run_x0 - pad, y_screen - pad,
                 run_x1 + pad, y_screen + fh + pad],
                radius=6, fill=(60, 50, 10)
            )

        # Pass 3 — draw characters
        for ch, cx, cw, _, st in char_data:
            if st == "past":
                color = COLOR_PAST
            elif st == "current":
                color = COLOR_CURRENT
            else:
                color = COLOR_TITLE if li == 0 else COLOR_FUTURE
            draw.text((cx, y_screen), ch, font=seg_font, fill=color)

    # Progress bar
    if tokens:
        end_t    = tokens[-1]["end"]
        progress = min(1.0, t / end_t) if end_t > 0 else 0
        bar_y    = HEIGHT - 16
        bh, bx0, bx1 = 5, H_PADDING, WIDTH - H_PADDING
        draw.rectangle([bx0, bar_y, bx1, bar_y + bh], fill=(35, 38, 50))
        draw.rectangle([bx0, bar_y,
                        bx0 + int((bx1 - bx0) * progress), bar_y + bh],
                       fill=COLOR_PROGRESS)

    return img


# ── Target camera position ────────────────────────────────────────────────────

def target_camera_y(tokens, current_idx, layout, viewport_h):
    """Y-offset that centres the current token's line in the viewport."""
    if current_idx < 0:
        return 0.0
    cur_li = tokens[current_idx]["line_idx"]
    for item in layout:
        if item["li"] == cur_li:
            fh     = item["fh"]
            lh     = int(fh * LINE_SPACING)
            target = item["y_abs"] - (viewport_h // 2) + (lh // 2)
            if layout:
                last     = layout[-1]
                total_h  = last["y_abs"] + int(last["fh"] * LINE_SPACING)
                max_scroll = max(0, total_h - viewport_h)
                return max(0.0, min(float(target), float(max_scroll)))
            return max(0.0, float(target))
    return 0.0


# ── Main ──────────────────────────────────────────────────────────────────────

def generate(story_path, audio_path, output_path, model_name="small", lang="zh-CN"):
    story_path  = Path(story_path)
    audio_path  = Path(audio_path)
    output_path = Path(output_path)
    stype       = script_type(lang)

    print(f"── Language: {lang}  script: {stype}")
    print("── Extracting narrative…")
    title, narrative_lines = extract_narrative(story_path)
    all_lines = [title] + narrative_lines
    print(f"  Title: {title}")
    for l in narrative_lines:
        print(f"  {l}")

    print("── Getting audio duration…")
    duration = audio_duration(audio_path)
    print(f"  {duration:.1f}s")

    print("── Running Whisper alignment…")
    wh_words = transcribe(audio_path, model_name, lang)
    print(f"  Got {len(wh_words)} Whisper tokens")

    print("── Building karaoke timeline…")
    tokens = build_timeline(all_lines, wh_words, stype)
    print(f"  Mapped {len(tokens)} display tokens")

    font       = ImageFont.truetype(str(FONT_PATH), FONT_SIZE)
    title_font = ImageFont.truetype(str(FONT_PATH), TITLE_FONT_SIZE)

    _ref_img  = Image.new("RGB", (10, 10))
    _ref_draw = ImageDraw.Draw(_ref_img)

    layout     = compute_layout(all_lines, font, title_font, _ref_draw, stype)
    viewport_h = HEIGHT - SCROLL_PAD - PROGRESS_H

    total_frames = int((duration + 1.5) * FPS)
    print(f"── Rendering {total_frames} frames @ {FPS} fps…")

    camera_y = 0.0

    with tempfile.TemporaryDirectory() as tmpdir:
        for fn in range(total_frames):
            t       = fn / FPS
            cur_idx = active_token_index(tokens, t)
            tgt     = target_camera_y(tokens, cur_idx, layout, viewport_h)
            camera_y += (tgt - camera_y) * SCROLL_EASE

            img = render_frame(all_lines, tokens, cur_idx, t,
                               font, title_font, layout, camera_y)
            img.save(os.path.join(tmpdir, f"f{fn:06d}.png"))

            if fn % (FPS * 5) == 0:
                print(f"  {fn}/{total_frames}  t={t:.1f}s  tok={cur_idx}")

        print("── Assembling video with FFmpeg…")
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", os.path.join(tmpdir, "f%06d.png"),
            "-i", str(audio_path),
            "-c:v", "libx264", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output_path),
        ], check=True, capture_output=True)

    print(f"\n✓ Video saved → {output_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Generate a karaoke-style video for a language learning story."
    )
    ap.add_argument("--story",  required=True, help="Path to story.md")
    ap.add_argument("--audio",  required=True, help="Path to narration audio (.mp3)")
    ap.add_argument("--output", required=True, help="Output path (.mp4)")
    ap.add_argument("--lang",   default="zh-CN",
                    help="TTS language code, e.g. zh-CN, en-US, fr-FR (default: zh-CN)")
    ap.add_argument("--model",  default="small",
                    help="Whisper model: tiny | base | small (default: small)")
    args = ap.parse_args()
    generate(args.story, args.audio, args.output, args.model, args.lang)
