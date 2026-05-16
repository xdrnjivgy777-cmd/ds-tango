"""
generate_review_md.py — Build the Japanese proofreading Markdown
from vocabulary_draft.json, following PRD §5.4 format.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

DS_TANGO = Path("/Users/shanlei/Desktop/ds-tango")
INPUT = DS_TANGO / "data" / "vocabulary_draft.json"
OUTPUT = DS_TANGO / "docs" / f"japanese_review_v{date.today().isoformat()}.md"


HEADER = """# データサイエンス・AI科 単語特訓 — 日本語校正シート

校正者：________________  日付：________________

校正方法：
- 「OK」列に問題なければ ✓ を記入
- 修正が必要な場合、「修正案」列に書いてください
- 不自然な表現、専門用語として不適切なもの、より良い例文があれば遠慮なくご指摘ください
- 振り仮名（reading）に誤りがあれば「修正案」に併記してください

カテゴリ別に並べています（同じ分野の語をまとめて見られるように）。

"""


def md_escape(s: str) -> str:
    """Escape | and newline so the table doesn't break."""
    return s.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    words = data["words"]
    # Group by primary tag
    by_cat: dict[str, list[dict]] = {}
    for w in words:
        cat = w["tags"][0] if w.get("tags") else "未分類"
        by_cat.setdefault(cat, []).append(w)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        f.write(HEADER)
        f.write(f"**総数**: {len(words)} 語  **カテゴリ数**: {len(by_cat)}\n\n")
        # Order: 統計学 → 機械学習 → データベース → Python → 可視化 → 前処理 → 業務
        order = ["統計学", "機械学習", "データベース", "Python", "可視化", "前処理", "業務"]
        ordered_cats = [c for c in order if c in by_cat] + [c for c in by_cat if c not in order]
        for cat in ordered_cats:
            entries = by_cat[cat]
            f.write(f"\n## {cat}（{len(entries)}語）\n\n")
            f.write("| ID | 単語 | 振り仮名 | 日本語定義 | 例文 | 定義OK | 例文OK | 修正案 |\n")
            f.write("|---|---|---|---|---|---|---|---|\n")
            for w in entries:
                jp = w["jp"]
                f.write(
                    f"| {w['id']} "
                    f"| {md_escape(jp['word'])} "
                    f"| {md_escape(jp['reading'])} "
                    f"| {md_escape(jp['definition'])} "
                    f"| {md_escape(jp['example'])} "
                    f"| ☐ | ☐ |  |\n"
                )

    print(f"Wrote: {OUTPUT}")
    print(f"Size: {OUTPUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
