#!/usr/bin/env python3
"""
karaoke.py - Generate a karaoke-style video from a language learning story.

The video displays the story text on screen, highlighting each word/character
in sync with the narration audio — like karaoke lyrics.

Usage:
    venv/bin/python tools/karaoke.py \\
        --story materials/chinese/stories/HSK1/surreal_meeting/story.md \\
        --audio materials/chinese/stories/HSK1/surreal_meeting/narration.mp3 \\
        --output materials/chinese/stories/HSK1/surreal_meeting/karaoke.mp4
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
TITLE_FONT_SIZE = 62                # title is slightly larger than body
LINE_SPACING    = 1.55              # multiplier on font height
TITLE_POST_GAP  = 50               # extra pixels below title before story text
H_PADDING       = 100              # horizontal padding
SCROLL_PAD      = 40               # top/bottom padding for the scroll viewport
PROGRESS_H      = 28               # height reserved at bottom for progress bar

FONT_PATH = Path(__file__).parent / "NotoSansSC-Regular.ttf"

# Smooth scroll speed: fraction of distance covered per frame
SCROLL_EASE = 0.12


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


def wrap_line(line: str, font, max_width: int, draw) -> list[str]:
    """Wrap a Chinese line (break anywhere) to fit max_width pixels."""
    segments, current = [], ""
    for ch in line:
        trial = current + ch
        w = draw.textbbox((0, 0), trial, font=font)[2]
        if w > max_width and current:
            segments.append(current)
            current = ch
        else:
            current = trial
    if current:
        segments.append(current)
    return segments


def compute_layout(all_lines, font, title_font, draw_ref):
    """
    Compute the scroll layout for all lines (title + story).

    Returns a list of segment dicts:
        { li, seg, offset, y_abs, seg_font, fh }

    all_lines[0] is the title; all_lines[1:] are story lines.
    The title gets TITLE_POST_GAP extra space below it.
    """
    available_w = WIDTH - 2 * H_PADDING
    body_fh  = draw_ref.textbbox((0, 0), "字", font=font)[3]
    title_fh = draw_ref.textbbox((0, 0), "字", font=title_font)[3]

    items = []
    y = 0
    for li, line in enumerate(all_lines):
        is_title = (li == 0)
        seg_font = title_font if is_title else font
        fh       = title_fh  if is_title else body_fh
        lh       = int(fh * LINE_SPACING)

        segs = wrap_line(line, seg_font, available_w, draw_ref)
        offset = 0
        for seg_i, seg in enumerate(segs):
            items.append(dict(li=li, seg=seg, offset=offset,
                              y_abs=y, seg_font=seg_font, fh=fh))
            offset += len(seg)
            y += lh
            # Extra gap after the last segment of the title line
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


def transcribe(audio_path: Path, model_name: str):
    """Return a flat list of {text, start, end} dicts from Whisper."""
    print(f"  Loading Whisper '{model_name}' model…")
    model = whisper.load_model(model_name)
    print("  Transcribing…")
    result = model.transcribe(
        str(audio_path), language="zh", word_timestamps=True, verbose=False
    )
    words = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            t = w["word"].strip()
            if t:
                words.append({"text": t, "start": w["start"], "end": w["end"]})
    return words


# ── Timeline builder ──────────────────────────────────────────────────────────

def is_zh(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"

def is_notable(ch: str) -> bool:
    """Characters we want to track (CJK + common Chinese punctuation)."""
    return is_zh(ch) or ch in "，。！？：""''（）、「」…—"


def build_timeline(all_lines: list[str], whisper_words: list[dict]):
    """
    Build a list of token dicts:
        { char, global_idx, line_idx, char_idx, start, end }

    all_lines[0] is the title; the title characters should appear in the
    Whisper output first (since the narration announces the title before
    the story body).
    """
    # Flatten all chars with their position info
    flat = []   # (char, line_idx, char_idx_in_line, global_idx)
    for li, line in enumerate(all_lines):
        for ci, ch in enumerate(line):
            flat.append((ch, li, ci, len(flat)))

    # Extract CJK chars from whisper output with per-char timestamps
    wh_chars = []
    for w in whisper_words:
        zh_in_w = [c for c in w["text"] if is_zh(c)]
        n = len(zh_in_w)
        if n == 0:
            continue
        dur = w["end"] - w["start"]
        for i, c in enumerate(zh_in_w):
            wh_chars.append((c, w["start"] + dur * i / n,
                               w["start"] + dur * (i + 1) / n))

    # Greedy match: walk through our CJK chars and match them to whisper
    our_zh = [(ch, li, ci, gi) for ch, li, ci, gi in flat if is_zh(ch)]
    wi = 0
    zh_times = {}   # global_idx -> (start, end)

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

    # Build the final token list for all notable chars
    tokens = []
    last_end = 0.0
    for ch, li, ci, gi in flat:
        if not is_notable(ch):
            continue
        if gi in zh_times:
            t0, t1 = zh_times[gi]
            last_end = t1
        else:
            t0, t1 = last_end, last_end + 0.05
        tokens.append(dict(char=ch, line_idx=li, char_idx=ci,
                           global_idx=gi, start=t0, end=t1))
    return tokens


def active_token_index(tokens, t: float) -> int:
    """Return index of the last token whose start ≤ t, or -1."""
    idx = -1
    for i, tok in enumerate(tokens):
        if tok["start"] <= t:
            idx = i
    return idx


# ── Frame renderer ────────────────────────────────────────────────────────────

def char_status(tokens, current_idx: int):
    """Build a dict {(line_idx, char_idx): status} where status ∈ past/current/future."""
    s = {}
    for i, tok in enumerate(tokens):
        key = (tok["line_idx"], tok["char_idx"])
        if i < current_idx:
            s[key] = "past"
        elif i == current_idx:
            s[key] = "current"
        else:
            s[key] = "future"
    return s


def render_frame(all_lines, tokens, current_idx, t, font, title_font,
                 layout, camera_y):
    """Render a single karaoke frame."""
    img  = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    viewport_top    = SCROLL_PAD
    viewport_bottom = HEIGHT - PROGRESS_H
    viewport_h      = viewport_bottom - viewport_top

    statuses = char_status(tokens, current_idx)

    for item in layout:
        li, seg, offset = item["li"], item["seg"], item["offset"]
        y_abs = item["y_abs"]
        seg_font = item["seg_font"]
        fh = item["fh"]

        y_screen = viewport_top + y_abs - camera_y

        # Cull segments outside the viewport
        if y_screen + fh < viewport_top or y_screen > viewport_bottom:
            continue

        # Centre the segment horizontally
        seg_w = sum(draw.textbbox((0, 0), c, font=seg_font)[2] for c in seg)
        x = (WIDTH - seg_w) // 2

        for ci_local, ch in enumerate(seg):
            ci_orig = offset + ci_local
            status  = statuses.get((li, ci_orig), "future")
            cw      = draw.textbbox((0, 0), ch, font=seg_font)[2]

            if status == "current":
                pad = 4
                draw.rounded_rectangle(
                    [x - pad, y_screen - pad,
                     x + cw + pad, y_screen + fh + pad],
                    radius=6, fill=(60, 50, 10)
                )
                color = COLOR_CURRENT
            elif status == "past":
                color = COLOR_PAST
            else:
                # future: title uses its own colour, body uses standard future colour
                color = COLOR_TITLE if li == 0 else COLOR_FUTURE

            draw.text((x, y_screen), ch, font=seg_font, fill=color)
            x += cw

    # Progress bar
    if tokens:
        end_t    = tokens[-1]["end"]
        progress = min(1.0, t / end_t) if end_t > 0 else 0
        bar_y    = HEIGHT - 16
        bh       = 5
        bx0, bx1 = H_PADDING, WIDTH - H_PADDING
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

    # Find the first layout segment belonging to cur_li
    for item in layout:
        if item["li"] == cur_li:
            seg_y = item["y_abs"]
            fh    = item["fh"]
            lh    = int(fh * LINE_SPACING)
            target = seg_y - (viewport_h // 2) + (lh // 2)
            if layout:
                last = layout[-1]
                total_h = last["y_abs"] + int(last["fh"] * LINE_SPACING)
                max_scroll = max(0, total_h - viewport_h)
                return max(0.0, min(float(target), float(max_scroll)))
            return max(0.0, float(target))

    return 0.0


# ── Main ──────────────────────────────────────────────────────────────────────

def generate(story_path, audio_path, output_path, model_name="small"):
    story_path  = Path(story_path)
    audio_path  = Path(audio_path)
    output_path = Path(output_path)

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
    wh_words = transcribe(audio_path, model_name)
    print(f"  Got {len(wh_words)} Whisper tokens")

    print("── Building karaoke timeline…")
    tokens = build_timeline(all_lines, wh_words)
    print(f"  Mapped {len(tokens)} display tokens")

    # Load fonts
    font       = ImageFont.truetype(str(FONT_PATH), FONT_SIZE)
    title_font = ImageFont.truetype(str(FONT_PATH), TITLE_FONT_SIZE)

    # Reference draw surface for measurements
    _ref_img  = Image.new("RGB", (10, 10))
    _ref_draw = ImageDraw.Draw(_ref_img)

    # Pre-compute scroll layout (same every frame)
    layout = compute_layout(all_lines, font, title_font, _ref_draw)

    viewport_h = HEIGHT - SCROLL_PAD - PROGRESS_H

    total_frames = int((duration + 1.5) * FPS)   # +1.5 s tail

    print(f"── Rendering {total_frames} frames @ {FPS} fps…")

    camera_y = 0.0

    with tempfile.TemporaryDirectory() as tmpdir:
        for fn in range(total_frames):
            t = fn / FPS
            cur_idx = active_token_index(tokens, t)

            # Smooth camera scroll
            tgt = target_camera_y(tokens, cur_idx, layout, viewport_h)
            camera_y += (tgt - camera_y) * SCROLL_EASE

            img = render_frame(
                all_lines, tokens, cur_idx, t,
                font, title_font, layout, camera_y,
            )
            img.save(os.path.join(tmpdir, f"f{fn:06d}.png"))

            if fn % (FPS * 5) == 0:
                print(f"  {fn}/{total_frames}  t={t:.1f}s  tok={cur_idx}")

        print("── Assembling video with FFmpeg…")
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", os.path.join(tmpdir, "f%06d.png"),
            "-i", str(audio_path),
            "-c:v", "libx264", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    print(f"\n✓ Video saved → {output_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Generate a karaoke-style video for a language learning story."
    )
    ap.add_argument("--story",  required=True, help="Path to story.md")
    ap.add_argument("--audio",  required=True, help="Path to narration audio (.mp3)")
    ap.add_argument("--output", required=True, help="Output path (.mp4)")
    ap.add_argument("--model",  default="small",
                    help="Whisper model: tiny | base | small (default: small)")
    args = ap.parse_args()
    generate(args.story, args.audio, args.output, args.model)
