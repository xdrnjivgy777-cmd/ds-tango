"""
extract_candidates.py — Tokenize raw_text, build candidate term list.

Output: scripts/extraction/candidates.csv
Columns: word, reading, freq_total, course_count, top_courses, sample_sentence

Strategy:
- Tokenize with fugashi (UniDic).
- Build compound nouns by merging adjacent 名詞 tokens (handles 「回帰分析」
  being split into 「回帰」+「分析」).
- Drop N5/N4 blacklist, person names, single-char common words, digits, ASCII.
- Track per-course occurrence to favor cross-course terms.
- Capture one example sentence per word from the corpus (longest sentence
  ≤ 60 chars containing the word).
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

from fugashi import Tagger

from n5_n4_blacklist import is_blacklisted, BLACKLIST  # noqa: F401

RAW_DIR = Path("/Users/shanlei/Desktop/ds-tango/scripts/extraction/raw_text")
OUT_CSV = Path("/Users/shanlei/Desktop/ds-tango/scripts/extraction/candidates.csv")

tagger = Tagger()

# ---- Filters ----
# Single chars we never want
HIRAGANA_ONLY = re.compile(r"^[ぁ-んー]+$")
KATAKANA_ONLY = re.compile(r"^[ァ-ヴー・]+$")
NUMBERS_ONLY = re.compile(r"^[0-9０-９]+$")
ASCII_ONLY = re.compile(r"^[A-Za-z]+$")
HAS_KANJI = re.compile(r"[一-鿿]")
SENTENCE_SPLIT_RE = re.compile(r"[。！？\n]+")


def is_useful_pos(features) -> bool:
    """Accept only nouns that look like content words."""
    pos1 = features.pos1  # 大分類: 名詞 etc.
    pos2 = features.pos2  # 小分類
    pos3 = features.pos3
    if pos1 != "名詞":
        return False
    # Drop pronouns, numerals, person names, place names, time expressions
    if pos2 in {"代名詞", "数詞", "助動詞語幹"}:
        return False
    if pos2 == "固有名詞" and pos3 in {"人名", "地名"}:
        return False
    return True


def normalize(token) -> str | None:
    """Get the surface (or lemma if obviously normalized) for a token."""
    surface = token.surface
    # Drop punctuation that fugashi sometimes lets through
    if not surface or surface.isspace():
        return None
    if NUMBERS_ONLY.match(surface):
        return None
    if ASCII_ONLY.match(surface) and len(surface) <= 2:
        return None
    if HIRAGANA_ONLY.match(surface) and len(surface) <= 2:
        return None  # 「もの」「ため」など
    if KATAKANA_ONLY.match(surface) and len(surface) <= 1:
        return None
    return surface


def tokenize_sentence(sent: str):
    return list(tagger(sent))


def build_compound_words(tokens) -> list[tuple[str, str]]:
    """
    Walk tokens, emit (word, reading) tuples.
    Greedy-merge consecutive 名詞-* tokens into compound nouns,
    AND also yield each individual noun (so single-token terms are not lost).
    """
    out: list[tuple[str, str]] = []
    n = len(tokens)
    i = 0
    while i < n:
        t = tokens[i]
        if not is_useful_pos(t.feature):
            i += 1
            continue
        # Try to extend a compound
        j = i
        parts = []
        readings = []
        while j < n and is_useful_pos(tokens[j].feature):
            surf = normalize(tokens[j])
            if surf is None:
                break
            parts.append(surf)
            # Reading: prefer kana from feature
            r = getattr(tokens[j].feature, "kana", None) or tokens[j].surface
            readings.append(r)
            j += 1
        if not parts:
            i += 1
            continue
        # Emit individual tokens
        for p, r in zip(parts, readings):
            out.append((p, r))
        # Emit compound (length 2..4) — most DS terms are 2-4 morphemes
        if 2 <= len(parts) <= 4:
            compound = "".join(parts)
            compound_read = "".join(readings)
            out.append((compound, compound_read))
        i = j
    return out


def kana_to_hiragana(s: str) -> str:
    out = []
    for c in s:
        code = ord(c)
        if 0x30A1 <= code <= 0x30F6:  # katakana
            out.append(chr(code - 0x60))
        else:
            out.append(c)
    return "".join(out)


def main():
    word_freq: Counter[str] = Counter()
    word_reading: dict[str, str] = {}
    word_courses: dict[str, set[str]] = defaultdict(set)
    word_examples: dict[str, str] = {}

    txt_files = sorted(RAW_DIR.glob("*.txt"))
    print(f"Reading {len(txt_files)} course text files...")

    for txt in txt_files:
        course = txt.stem
        text = txt.read_text(encoding="utf-8")
        # Split into sentences for example capture
        sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
        for sent in sentences:
            if not HAS_KANJI.search(sent):
                continue
            tokens = tokenize_sentence(sent)
            seen_in_sent = set()
            for word, reading in build_compound_words(tokens):
                if is_blacklisted(word):
                    continue
                # Need at least 1 kanji OR be a katakana technical term ≥ 3 chars
                if not HAS_KANJI.search(word):
                    if not (KATAKANA_ONLY.match(word) and len(word) >= 3):
                        continue
                # Drop single-char compounds caught by accident
                if len(word) < 2:
                    continue
                word_freq[word] += 1
                word_courses[word].add(course)
                if word not in word_reading:
                    word_reading[word] = kana_to_hiragana(reading)
                if word not in seen_in_sent:
                    seen_in_sent.add(word)
                # Capture good example sentence (12-50 chars, contains word)
                if word not in word_examples and 12 <= len(sent) <= 50 and word in sent:
                    word_examples[word] = sent

    # Now build CSV. Sort by composite score: cross-course first, then freq.
    rows = []
    for word, freq in word_freq.items():
        if freq < 2:  # min frequency cutoff
            continue
        cc = len(word_courses[word])
        score = cc * 100 + freq
        rows.append({
            "word": word,
            "reading": word_reading.get(word, ""),
            "freq_total": freq,
            "course_count": cc,
            "top_courses": "|".join(sorted(word_courses[word])[:5]),
            "sample_sentence": word_examples.get(word, ""),
            "score": score,
        })
    rows.sort(key=lambda r: (-r["score"], -r["freq_total"], r["word"]))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "word", "reading", "freq_total", "course_count",
            "top_courses", "sample_sentence", "score"
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"\nWrote {len(rows)} candidates to {OUT_CSV}")
    print("\nTop 30 candidates:")
    for r in rows[:30]:
        print(f"  {r['word']:<12} freq={r['freq_total']:>4} courses={r['course_count']:>2}  reading={r['reading']}")


if __name__ == "__main__":
    main()
