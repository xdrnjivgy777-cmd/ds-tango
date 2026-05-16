"""
generate_audio_edge.py — Generate Japanese TTS mp3 files using Edge TTS.

Edge TTS is Microsoft Edge's built-in TTS backend, exposed as a free,
no-key-required API. Voice ja-JP-KeitaNeural is the same as in Azure TTS.

Usage:
    python generate_audio_edge.py [--only-missing] [--limit N] [--concurrency K]

Output: /Users/shanlei/Desktop/ds-tango/audio/{ID}_{japanese_word}_{type}.mp3
Format: mp3 (Edge default; ~24kHz mono)

900 files (300 words × 3 types) take ~10 minutes with concurrency=8.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import edge_tts

DS_TANGO = Path("/Users/shanlei/Desktop/ds-tango")
INPUT = DS_TANGO / "data" / "vocabulary.json"
AUDIO_DIR = DS_TANGO / "audio"

VOICE = "ja-JP-KeitaNeural"
RATE = "+0%"
VOLUME = "+0%"


async def synth_one(text: str, out_path: Path, attempt: int = 1) -> tuple[bool, str]:
    """Synthesize one text -> mp3 file. Return (success, info)."""
    try:
        comm = edge_tts.Communicate(text, VOICE, rate=RATE, volume=VOLUME)
        await comm.save(str(out_path))
        if out_path.stat().st_size < 200:
            raise RuntimeError(f"too small ({out_path.stat().st_size} bytes)")
        return True, "ok"
    except Exception as e:
        if attempt < 3:
            await asyncio.sleep(1.0 * attempt)
            return await synth_one(text, out_path, attempt + 1)
        # Clean up empty/partial file
        try:
            if out_path.exists() and out_path.stat().st_size < 200:
                out_path.unlink()
        except Exception:
            pass
        return False, f"{type(e).__name__}: {e}"


async def worker(queue: asyncio.Queue, results: list, semaphore: asyncio.Semaphore, progress: dict):
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
        idx, total, text, out = item
        async with semaphore:
            ok, info = await synth_one(text, out)
        progress["done"] += 1
        results.append((ok, out.name, info))
        if progress["done"] % 50 == 0 or progress["done"] == total:
            elapsed = time.time() - progress["start"]
            print(f"  [{progress['done']:>3}/{total}] {elapsed:>5.1f}s — {out.name}", flush=True)
        queue.task_done()


async def main_async(args):
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    words = data["words"]
    if args.limit:
        words = words[: args.limit]

    # Build task list
    tasks = []
    for w in words:
        wid = w["id"]
        jpw = w["jp"]["word"]
        targets = [
            ("word", w["jp"]["word"]),
            ("def", w["jp"]["definition"]),
            ("ex", w["jp"]["example"]),
        ]
        for kind, text in targets:
            out = AUDIO_DIR / f"{wid}_{jpw}_{kind}.mp3"
            if args.only_missing and out.exists() and out.stat().st_size > 200:
                continue
            tasks.append((text, out))

    total = len(tasks)
    print(f"To synthesize: {total} mp3 files (voice={VOICE}, concurrency={args.concurrency})")
    if total == 0:
        print("Nothing to do.")
        return

    queue = asyncio.Queue()
    for i, (text, out) in enumerate(tasks, 1):
        await queue.put((i, total, text, out))
    for _ in range(args.concurrency):
        await queue.put(None)

    sem = asyncio.Semaphore(args.concurrency)
    progress = {"done": 0, "start": time.time()}
    results = []
    workers = [asyncio.create_task(worker(queue, results, sem, progress))
               for _ in range(args.concurrency)]
    await asyncio.gather(*workers)

    elapsed = time.time() - progress["start"]
    ok = sum(1 for r in results if r[0])
    fail = total - ok
    print(f"\nDone in {elapsed:.1f}s. ok={ok} fail={fail}")
    if fail:
        print("Failures:")
        for r in results:
            if not r[0]:
                print(f"  {r[1]}: {r[2]}")
        sys.exit(1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--only-missing", action="store_true",
                   help="Skip files that already exist (and non-empty)")
    p.add_argument("--limit", type=int, default=0,
                   help="Process only the first N words (for testing)")
    p.add_argument("--concurrency", type=int, default=8,
                   help="Parallel requests (default 8)")
    args = p.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
