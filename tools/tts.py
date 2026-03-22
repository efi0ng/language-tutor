#!/usr/bin/env python3
"""Text-to-speech tool using edge-tts.

Usage:
    python tools/tts.py --text "你好世界" --output story.mp3 --lang zh-CN
    python tools/tts.py --file story.txt --output story.mp3 --lang zh-CN
    python tools/tts.py --list-voices zh-CN

Supports any language that edge-tts supports. Common language codes:
    zh-CN   Chinese (Simplified)
    ja-JP   Japanese
    ko-KR   Korean
    fr-FR   French
    de-DE   German
    es-ES   Spanish
    en-US   English (US)
"""

import argparse
import asyncio
import sys

import edge_tts

# Preferred voices per language (natural-sounding defaults)
DEFAULT_VOICES = {
    "zh-CN": "zh-CN-XiaoxiaoNeural",
    "zh-TW": "zh-TW-HsiaoChenNeural",
    "ja-JP": "ja-JP-NanamiNeural",
    "ko-KR": "ko-KR-SunHiNeural",
    "fr-FR": "fr-FR-DeniseNeural",
    "de-DE": "de-DE-KatjaNeural",
    "es-ES": "es-ES-ElviraNeural",
    "it-IT": "it-IT-ElsaNeural",
    "pt-BR": "pt-BR-FranciscaNeural",
    "en-US": "en-US-JennyNeural",
    "en-GB": "en-GB-SoniaNeural",
    "ru-RU": "ru-RU-SvetlanaNeural",
    "th-TH": "th-TH-PremwadeeNeural",
    "vi-VN": "vi-VN-HoaiMyNeural",
}


async def list_voices(lang_prefix: str | None = None):
    voices = await edge_tts.list_voices()
    for v in voices:
        if lang_prefix and not v["ShortName"].startswith(lang_prefix):
            continue
        print(f"{v['ShortName']:40s} {v['Gender']:10s} {v.get('FriendlyName', '')}")


async def synthesize(text: str, output: str, voice: str, rate: str = "+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output)


def main():
    parser = argparse.ArgumentParser(description="Text-to-speech using edge-tts")
    parser.add_argument("--text", help="Text to synthesize")
    parser.add_argument("--file", help="File containing text to synthesize")
    parser.add_argument("--output", "-o", help="Output MP3 file path")
    parser.add_argument("--lang", default="zh-CN", help="Language code (e.g. zh-CN, ja-JP)")
    parser.add_argument("--voice", help="Specific voice name (overrides --lang default)")
    parser.add_argument("--rate", default="-10%", help="Speech rate adjustment (default: -10%%)")
    parser.add_argument("--list-voices", nargs="?", const="", metavar="LANG",
                        help="List available voices, optionally filtered by language prefix")

    args = parser.parse_args()

    if args.list_voices is not None:
        asyncio.run(list_voices(args.list_voices or None))
        return

    if not args.text and not args.file:
        parser.error("Either --text or --file is required")
    if not args.output:
        parser.error("--output is required")

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = args.text

    voice = args.voice or DEFAULT_VOICES.get(args.lang)
    if not voice:
        print(f"No default voice for '{args.lang}'. Use --voice to specify one, "
              f"or --list-voices {args.lang} to see options.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(synthesize(text, args.output, voice, args.rate))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
