"""
generate_audio.py — Generate Azure Neural TTS mp3 files for every Japanese word/definition/example
in vocabulary_draft.json.

Usage (run locally):
    export AZURE_SPEECH_KEY=xxx
    export AZURE_SPEECH_REGION=japaneast   # or your region
    python generate_audio.py [--only-missing]

Voice: ja-JP-KeitaNeural (per PRD)
Format: 24kHz, 48kbps mono mp3
Output: /Users/shanlei/Desktop/ds-tango/audio/{ID}_{word}_{type}.mp3

Notes:
- Costs zero for ~17,400 chars (Azure Neural TTS free tier = 500K chars/month)
- AZURE_SPEECH_KEY is read from env, NEVER committed to repo
- Use --only-missing to skip files that already exist (cheap re-runs)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DS_TANGO = Path("/Users/shanlei/Desktop/ds-tango")
INPUT = DS_TANGO / "data" / "vocabulary_draft.json"
AUDIO_DIR = DS_TANGO / "audio"

VOICE = "ja-JP-KeitaNeural"


def get_synthesizer():
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        sys.exit(
            "Missing dependency. Install with:\n"
            "    pip install azure-cognitiveservices-speech"
        )

    key = os.environ.get("AZURE_SPEECH_KEY")
    region = os.environ.get("AZURE_SPEECH_REGION", "japaneast")
    if not key:
        sys.exit("AZURE_SPEECH_KEY env var is required.")

    config = speechsdk.SpeechConfig(subscription=key, region=region)
    config.speech_synthesis_voice_name = VOICE
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3
    )
    return speechsdk, config


def synth_one(speechsdk, config, text: str, out_path: Path) -> bool:
    audio_cfg = speechsdk.audio.AudioOutputConfig(filename=str(out_path))
    synth = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=audio_cfg)
    result = synth.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    print(f"  [fail] {out_path.name}: {result.reason} {getattr(result, 'cancellation_details', '')}")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-missing", action="store_true",
                        help="Skip files that already exist")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only the first N words (for testing)")
    args = parser.parse_args()

    speechsdk, config = get_synthesizer()
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    words = data["words"]
    if args.limit:
        words = words[:args.limit]

    total_files = 0
    new_files = 0
    failed = 0
    for w in words:
        wid = w["id"]
        jpw = w["jp"]["word"]
        targets = [
            ("word", w["jp"]["word"]),
            ("def", w["jp"]["definition"]),
            ("ex", w["jp"]["example"]),
        ]
        for kind, text in targets:
            total_files += 1
            fname = f"{wid}_{jpw}_{kind}.mp3"
            out = AUDIO_DIR / fname
            if args.only_missing and out.exists():
                continue
            ok = synth_one(speechsdk, config, text, out)
            if ok:
                new_files += 1
            else:
                failed += 1

    print(f"\nTotal target files: {total_files}")
    print(f"Synthesized this run: {new_files}")
    print(f"Failed: {failed}")
    print(f"Audio dir: {AUDIO_DIR}")


if __name__ == "__main__":
    main()
