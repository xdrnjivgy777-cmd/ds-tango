"""
merge_batches.py — Merge 3 agent-produced batch JSON files into vocabulary_draft.json.

Validates:
- Each batch has the expected number of entries
- IDs are continuous, no duplicates, no missing
- Each entry has all required schema fields
- All 7 translation languages present
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

CWD_BATCHES = Path("/Users/shanlei/Desktop/学校/AAA専門学校東京テクニカルカレッジ")
DS_TANGO = Path("/Users/shanlei/Desktop/ds-tango")
OUTPUT = DS_TANGO / "data" / "vocabulary_draft.json"

REQUIRED_LANGS = ["en", "zh", "my", "mn", "id", "ne"]
REQUIRED_TOP_KEYS = ["id", "level", "tags", "frequency", "jp", "translations", "audio", "review_status"]
REQUIRED_JP_KEYS = ["word", "reading", "definition", "example"]
REQUIRED_TR_KEYS = ["word", "definition", "example"]


def load_batch(num: int) -> list[dict]:
    # Try CWD first, then ds-tango location
    paths = [
        CWD_BATCHES / f"batch_{num}_output.json",
        DS_TANGO / "scripts" / "extraction" / "batches" / f"batch_{num}_output.json",
    ]
    for p in paths:
        if p.exists():
            print(f"Loading batch {num} from: {p}")
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"batch_{num}_output.json not found in {paths}")


def validate_entry(e: dict, expected_id: str) -> list[str]:
    errors = []
    if e.get("id") != expected_id:
        errors.append(f"id mismatch: got {e.get('id')!r}, expected {expected_id!r}")
    for k in REQUIRED_TOP_KEYS:
        if k not in e:
            errors.append(f"missing top key: {k}")
    if "jp" in e:
        for k in REQUIRED_JP_KEYS:
            if k not in e["jp"] or not e["jp"][k]:
                errors.append(f"jp.{k} missing or empty")
    if "translations" in e:
        for lang in REQUIRED_LANGS:
            if lang not in e["translations"]:
                errors.append(f"translations.{lang} missing")
                continue
            for k in REQUIRED_TR_KEYS:
                if k not in e["translations"][lang] or not e["translations"][lang][k]:
                    errors.append(f"translations.{lang}.{k} missing or empty")
    return errors


def main():
    # Load and validate all batches
    all_entries = []
    expected_id = 1
    total_errors = 0
    for batch_num in (1, 2, 3):
        try:
            batch = load_batch(batch_num)
        except FileNotFoundError as e:
            print(f"  ERROR: {e}")
            sys.exit(1)
        if len(batch) != 100:
            print(f"  WARN: batch {batch_num} has {len(batch)} entries (expected 100)")
        for e in batch:
            errors = validate_entry(e, f"{expected_id:04d}")
            if errors:
                total_errors += len(errors)
                print(f"  [id {e.get('id', '?')}] {len(errors)} errors:")
                for err in errors[:3]:
                    print(f"    - {err}")
                if len(errors) > 3:
                    print(f"    - ... and {len(errors) - 3} more")
            all_entries.append(e)
            expected_id += 1
    print(f"\nTotal entries: {len(all_entries)}")
    print(f"Total validation errors: {total_errors}")

    # Build final vocabulary_draft.json
    output = {
        "_meta": {
            "version": "draft-1",
            "generated_date": "2026-05-16",
            "total": len(all_entries),
            "languages": ["jp"] + REQUIRED_LANGS,
            "verified_languages": ["zh", "en"],
            "pending_review_languages": ["jp", "my", "mn", "id", "ne"],
            "notes": "Japanese definitions/examples need native-speaker review (verified_jp=false). Minority-language translations are AI-generated (verified_my/mn/id/ne=false)."
        },
        "words": all_entries,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote: {OUTPUT}")
    print(f"Size: {OUTPUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
