#!/usr/bin/env python3
"""One-time setup: download CC-CEDICT and build cedict_hsk.json.

Downloads the CC-CEDICT dictionary, cross-references it against the HSK 3.0
vocabulary list, and saves per-word English definitions to tools/data/cedict_hsk.json.

Run once before the first assessment:
    venv/bin/python tools/build_cedict.py

The output file is committed to the repo so students don't need to re-run this.
"""

import csv
import gzip
import json
import os
import re
import sys
import urllib.request

CEDICT_URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"
CEDICT_GZ  = os.path.join(os.path.dirname(__file__), "data", "cedict.u8.gz")
HSK_CSV    = os.path.join(os.path.dirname(__file__), "data", "hsk30.csv")
OUT_JSON   = os.path.join(os.path.dirname(__file__), "data", "cedict_hsk.json")

# CC-CEDICT line pattern: Traditional Simplified [tones] /def1/def2/.../
CEDICT_RE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$")


def download_cedict():
    if os.path.exists(CEDICT_GZ):
        print(f"Using cached {CEDICT_GZ}")
        return
    print(f"Downloading CC-CEDICT from {CEDICT_URL} ...")
    urllib.request.urlretrieve(CEDICT_URL, CEDICT_GZ)
    print(f"Saved to {CEDICT_GZ}")


def load_cedict_raw():
    """Return dict: 'Traditional Simplified [tones]' → [def1, def2, ...]"""
    entries = {}
    with gzip.open(CEDICT_GZ, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#"):
                continue
            m = CEDICT_RE.match(line)
            if not m:
                continue
            trad, simp, tones, defs_str = m.groups()
            key = f"{trad} {simp} [{tones}]"
            defs = [d.strip() for d in defs_str.split("/") if d.strip()]
            entries[key] = defs
    print(f"Loaded {len(entries):,} CC-CEDICT entries.")
    return entries


def parse_level(level_str):
    try:
        return int(level_str)
    except ValueError:
        return int(level_str.split("-")[0])


def build_hsk_json(cedict_raw):
    """Cross-reference hsk30.csv against CC-CEDICT, return the output dict."""
    output = {}
    matched = 0
    unmatched = []

    with open(HSK_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        level = parse_level(row["Level"].strip())
        pinyin = row["Pinyin"].strip()
        pos = row["POS"].strip()
        cedict_ref = row["CEDICT"].strip()

        # Build lookup key from CEDICT column: "Trad|Simp[tones]" → "Trad Simp [tones]"
        cedict_key = None
        defs = []
        if cedict_ref:
            # Format is always: Traditional|Simplified[tones]
            m = re.match(r"^([^|]+)\|([^\[]+)\[([^\]]+)\]", cedict_ref)
            if m:
                trad  = m.group(1).strip()
                simp  = m.group(2).strip()
                tones = m.group(3).strip()
                cedict_key = f"{trad} {simp} [{tones}]"

            if cedict_key and cedict_key in cedict_raw:
                defs = cedict_raw[cedict_key]
                matched += 1
            else:
                unmatched.append(row["Simplified"])

        # Collect all simplified and traditional variants
        all_simplified = [v.strip() for v in row["Simplified"].split("|") if v.strip()]
        all_traditional = [v.strip() for v in row["Traditional"].split("|") if v.strip()]

        # Emit one entry per simplified variant (so lookup by simplified word works directly)
        for simp_variant in all_simplified:
            if simp_variant not in output:
                output[simp_variant] = {
                    "simplified": simp_variant,
                    "all_simplified": all_simplified,
                    "traditional": all_traditional[0] if all_traditional else simp_variant,
                    "all_traditional": all_traditional,
                    "pinyin": pinyin.split("|")[0].strip(),  # take first if pipe-separated
                    "pos": pos,
                    "level": level,
                    "definitions": defs,
                }

    return output, matched, unmatched


def main():
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)

    try:
        download_cedict()
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        print("Try downloading manually and placing at:", CEDICT_GZ, file=sys.stderr)
        sys.exit(1)

    cedict_raw = load_cedict_raw()
    output, matched, unmatched = build_hsk_json(cedict_raw)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total = len(output)
    print(f"\nDone.")
    print(f"  Entries written : {total:,}")
    print(f"  CEDICT matched  : {matched:,}")
    print(f"  Unmatched       : {len(unmatched):,}")
    if unmatched:
        print(f"  First 10 unmatched: {unmatched[:10]}")
    print(f"  Output          : {OUT_JSON}")


if __name__ == "__main__":
    main()
