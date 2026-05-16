"""
make_poster.py — Generate a print-ready A4 poster (HTML) with QR code.

Open the resulting poster.html in any browser → File > Print > Save as PDF.
Then print on A4 paper at 100% scale.
"""

from pathlib import Path
import qrcode
import qrcode.image.svg

OUT_DIR = Path("/Users/shanlei/Desktop/ds-tango/mockup")
APP_URL = "https://xdrnjivgy777-cmd.github.io/ds-tango/"


def generate_qr_path(url: str) -> tuple[str, int]:
    """Return the QR path 'd' string and viewBox edge length."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=0,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    svg_bytes = img.to_string()
    s = svg_bytes.decode("utf-8")
    # Parse d="..." and viewBox
    import re
    d_match = re.search(r'd="([^"]+)"', s)
    vb_match = re.search(r'viewBox="0 0 (\d+) (\d+)"', s)
    if not d_match or not vb_match:
        raise RuntimeError("Could not parse generated QR SVG")
    return d_match.group(1), int(vb_match.group(1))


HTML_TMPL = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>DS単語 — A4 ポスター</title>
<style>
  /* A4 = 210mm × 297mm portrait */
  @page {{ size: A4 portrait; margin: 0; }}

  :root {{
    --bg: #FFFFFF;
    --text: #000000;
    --muted: #666666;
    --faint: #999999;
    --divider: #E5E5E5;
    --font-jp: "Hiragino Kaku Gothic ProN", "Yu Gothic", "Noto Sans JP", -apple-system, sans-serif;
    --font-my: "Noto Sans Myanmar", "Padauk", sans-serif;
    --font-mn: "Noto Sans Mongolian", sans-serif;
    --font-ne: "Noto Sans Devanagari", sans-serif;
  }}

  * {{ box-sizing: border-box; }}

  html, body {{
    margin: 0;
    padding: 0;
    background: #f0f0ee;
    font-family: var(--font-jp);
    color: var(--text);
    -webkit-font-smoothing: antialiased;
  }}

  /* Screen view: center the A4 sheet with a subtle shadow */
  @media screen {{
    body {{
      display: flex;
      justify-content: center;
      padding: 24px;
    }}
    .sheet {{
      box-shadow: 0 8px 32px rgba(0,0,0,0.08);
    }}
    .print-hint {{
      position: fixed;
      bottom: 16px;
      left: 50%;
      transform: translateX(-50%);
      background: var(--text);
      color: #fff;
      padding: 10px 18px;
      border-radius: 999px;
      font-size: 13px;
    }}
  }}
  @media print {{
    body {{ background: #fff; }}
    .print-hint {{ display: none; }}
  }}

  .sheet {{
    width: 210mm;
    min-height: 297mm;
    background: var(--bg);
    padding: 24mm 22mm 20mm;
    display: flex;
    flex-direction: column;
    page-break-after: always;
  }}

  /* ---- Top brand block ---- */
  .brand-block {{
    text-align: center;
  }}
  .brand-name {{
    font-size: 56pt;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 0;
    line-height: 1;
  }}
  .brand-sub {{
    font-size: 13pt;
    color: var(--muted);
    margin: 8mm 0 0;
    letter-spacing: 0.05em;
    line-height: 1.55;
  }}
  .brand-tag {{
    display: inline-block;
    margin-top: 6mm;
    font-size: 9pt;
    letter-spacing: 0.15em;
    color: var(--faint);
    border: 1px solid var(--divider);
    padding: 2mm 5mm;
    border-radius: 999px;
    text-transform: uppercase;
  }}

  /* ---- QR ---- */
  .qr-wrap {{
    margin: 16mm auto 8mm;
    width: 95mm;
    height: 95mm;
    padding: 5mm;
    border: 1px solid var(--divider);
    border-radius: 6mm;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
  }}
  .qr-wrap svg {{
    width: 100%;
    height: 100%;
    display: block;
  }}

  .url-line {{
    text-align: center;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 10.5pt;
    color: var(--text);
    word-break: break-all;
    margin: 0;
  }}
  .url-hint {{
    text-align: center;
    font-size: 9pt;
    color: var(--faint);
    margin: 1.5mm 0 0;
    letter-spacing: 0.05em;
  }}

  /* ---- Headline ---- */
  .headline-block {{
    margin: 16mm 0 0;
    text-align: center;
  }}
  .headline-jp {{
    font-size: 17pt;
    font-weight: 600;
    line-height: 1.45;
    margin: 0;
    letter-spacing: 0.01em;
  }}

  /* ---- Multilingual one-liners ---- */
  .ml-block {{
    margin: 12mm 0 0;
    border-top: 1px solid var(--divider);
    padding-top: 8mm;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4mm 12mm;
  }}
  .ml-row {{
    display: flex;
    flex-direction: column;
    gap: 1mm;
  }}
  .ml-lang {{
    font-size: 8pt;
    color: var(--faint);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }}
  .ml-text {{
    font-size: 10pt;
    line-height: 1.4;
    color: var(--text);
  }}
  .ml-text[lang="my"] {{ font-family: var(--font-my); font-size: 10pt; }}
  .ml-text[lang="mn"] {{ font-family: var(--font-mn); }}
  .ml-text[lang="ne"] {{ font-family: var(--font-ne); font-size: 10pt; }}

  /* ---- Footer ---- */
  .footer {{
    margin-top: auto;
    padding-top: 8mm;
    border-top: 1px solid var(--divider);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 8.5pt;
    color: var(--faint);
    letter-spacing: 0.04em;
  }}
  .footer-features {{
    display: flex;
    gap: 6mm;
  }}
  .footer-features span::before {{
    content: "✓ ";
    color: var(--text);
  }}
</style>
</head>
<body>
  <div class="sheet">

    <div class="brand-block">
      <h1 class="brand-name">DS単語</h1>
      <p class="brand-sub">データサイエンス・AI科<br>専門用語 特訓アプリ</p>
      <div class="brand-tag">300 words · 7 languages · audio</div>
    </div>

    <div class="qr-wrap">
      <svg viewBox="0 0 {qr_size} {qr_size}" xmlns="http://www.w3.org/2000/svg">
        <path d="{qr_path}" fill="#000000"/>
      </svg>
    </div>

    <p class="url-line">{url}</p>
    <p class="url-hint">スマホのカメラで QR コードを読み取ってください</p>

    <div class="headline-block">
      <p class="headline-jp">「回帰分析」「正規化」「特徴量」…<br>授業で出てくる専門用語を、ひと月で覚える。</p>
    </div>

    <div class="ml-block">
      <div class="ml-row">
        <span class="ml-lang">日本語</span>
        <span class="ml-text" lang="ja">スマホで読み取って、すぐに使えます。登録不要。</span>
      </div>
      <div class="ml-row">
        <span class="ml-lang">English</span>
        <span class="ml-text" lang="en">Scan with your phone — no install, no account.</span>
      </div>
      <div class="ml-row">
        <span class="ml-lang">中文</span>
        <span class="ml-text" lang="zh">扫一下手机即用，无需下载，无需注册。</span>
      </div>
      <div class="ml-row">
        <span class="ml-lang">မြန်မာ</span>
        <span class="ml-text" lang="my">ဖုန်းနဲ့ scan လုပ်ပြီး ချက်ချင်းသုံးနိုင်ပါသည်။ download မလိုပါ။</span>
      </div>
      <div class="ml-row">
        <span class="ml-lang">Монгол</span>
        <span class="ml-text" lang="mn">Гар утсаараа сканнердан, шууд ашиглаарай. Татаж авах шаардлагагүй.</span>
      </div>
      <div class="ml-row">
        <span class="ml-lang">Bahasa Indonesia</span>
        <span class="ml-text" lang="id">Pindai dengan ponselmu — tanpa install, tanpa akun.</span>
      </div>
      <div class="ml-row">
        <span class="ml-lang">नेपाली</span>
        <span class="ml-text" lang="ne">फोनबाट स्क्यान गर्नुहोस् — install र account आवश्यक छैन।</span>
      </div>
      <div class="ml-row">
        <span class="ml-lang">Features</span>
        <span class="ml-text">300語 · 7言語翻訳 · 日本語音声 · ホーム画面に追加可</span>
      </div>
    </div>

    <div class="footer">
      <div>DS単語 v0.1 · 2026-05</div>
      <div class="footer-features">
        <span>無料</span>
        <span>登録不要</span>
        <span>オフライン対応</span>
      </div>
    </div>

  </div>

  <div class="print-hint">⌘P → 保存 PDF または印刷（A4・100%）</div>
</body>
</html>
"""


def main():
    qr_path, qr_size = generate_qr_path(APP_URL)
    html = HTML_TMPL.format(qr_path=qr_path, qr_size=qr_size, url=APP_URL)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "poster.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html):,} bytes)")
    print(f"QR encodes: {APP_URL} ({qr_size}x{qr_size} modules)")
    print("Open in browser, then ⌘P → Save as PDF.")


if __name__ == "__main__":
    main()
