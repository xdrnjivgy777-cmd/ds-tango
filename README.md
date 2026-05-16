# DS単語 (DS-tango)

データサイエンス・AI科に通う外国人留学生のための、専門用語特訓PWA。
A vocabulary trainer for foreign exchange students studying Data Science / AI in Japanese.

**Live site**: https://xdrnjivgy777-cmd.github.io/ds-tango/

---

## What it does

- 約 300 語の DS 専門用語（統計学・機械学習・データベース・Python・可視化・前処理・業務）
- 各単語に日本語の意味と例文 + 6 言語の翻訳（English / 中文 / မြန်မာ / Монгол / Bahasa Indonesia / नेपाली）
- ja-JP-KeitaNeural 音声で日本語パートを読み上げ
- 「覚えた」を押すまで自動でくり返し出題（被動三态モデル）
- ブラウザの localStorage に進捗を保存。アカウント不要
- PWA：ホーム画面に追加、オフラインで利用可

## Architecture

Pure static site. No backend, no build step, no framework. Vanilla HTML + CSS + JS.

```
ds-tango/
├── index.html              # SPA shell — all views in one document
├── style.css
├── app.js                  # 3-state queue, card render, localStorage, audio, settings
├── i18n/ja.json            # UI text + per-language definition/example labels
├── data/vocabulary.json    # 300 words × 7 languages
├── audio/                  # 900 pre-generated mp3 files (300 words × {word, def, ex})
├── icons/                  # PWA icons
├── manifest.json           # PWA manifest
├── service-worker.js       # offline cache (lazy audio cache)
└── scripts/                # build-time helpers (not served)
    ├── extract_text.py     # PDFs/pptx → cleaned text
    ├── extract_candidates.py
    ├── categorize_candidates.py
    ├── merge_batches.py
    ├── generate_review_md.py
    ├── generate_audio_edge.py   # Edge TTS → mp3 batch
    └── make_icons.py
```

## Hosting

GitHub Pages, root of `main`. No build step.

## Audio

Pre-generated with Microsoft Edge TTS (`ja-JP-KeitaNeural`), no API key required.
To regenerate (e.g. after vocabulary updates):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install edge-tts
python scripts/generate_audio_edge.py --only-missing
```

## Vocabulary

The 300 words were extracted from anonymized course materials at AAA Tokyo Technical
College (Data Science / AI program), then hand-curated and translated. See:

- `data/vocabulary.json` — runtime data
- `docs/japanese_review_v*.md` — proofreading sheet for native Japanese speakers

Translation status (per `verified_*` fields in vocabulary.json):
- 日本語：要校正（日本人ネイティブによる校正待ち）
- English / 中文：Pico self-proofread
- ミャンマー語・モンゴル語・インドネシア語・ネパール語：AI 生成、各国の留学生による校正待ち

Spotted a translation issue? See in-app `Feedback` button.

## Privacy

- No tracking, no analytics, no account
- Progress stored only in your browser's localStorage
- Export / import JSON for cross-device backup (see Settings)

## License

Code: MIT
Vocabulary content (translations, definitions, examples): CC BY-NC-SA 4.0

Original course materials are not redistributed; only extracted, anonymized
domain terminology is published.

---

Built by Pico (xdrnjivgy777-cmd) with Claude. PRs and translation fixes welcome.
