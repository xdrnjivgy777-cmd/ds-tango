"""
make_icons.py — Generate placeholder PWA icons.

Produces icons/icon-192.png, icon-512.png, icon-maskable-512.png.
Uses Pillow. Run once locally. Replace later with proper logo.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ICONS_DIR = Path("/Users/shanlei/Desktop/ds-tango/icons")
ICONS_DIR.mkdir(parents=True, exist_ok=True)


def draw_icon(size: int, maskable: bool = False) -> Image.Image:
    """Draw a simple black-on-white icon with 'DS' text."""
    img = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # For maskable: keep the visual inside the inner 80% (safe zone)
    pad = int(size * 0.10) if maskable else int(size * 0.06)
    rect_size = size - pad * 2

    # Rounded black square containing the text
    radius = int(rect_size * 0.20)
    draw.rounded_rectangle(
        [(pad, pad), (pad + rect_size, pad + rect_size)],
        radius=radius,
        fill=(0, 0, 0, 255),
    )

    # Text "DS" — pick a font available on macOS
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ]
    font = None
    for fp in candidates:
        try:
            font = ImageFont.truetype(fp, int(rect_size * 0.50))
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    text = "DS"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx = pad + rect_size / 2
    cy = pad + rect_size / 2
    # Adjust for textbbox top-offset
    draw.text(
        (cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]),
        text,
        fill=(255, 255, 255, 255),
        font=font,
    )
    return img


def main():
    sizes = [
        (192, "icon-192.png", False),
        (512, "icon-512.png", False),
        (512, "icon-maskable-512.png", True),
    ]
    for size, name, maskable in sizes:
        img = draw_icon(size, maskable=maskable)
        out = ICONS_DIR / name
        img.save(out, "PNG", optimize=True)
        print(f"Wrote {out} ({size}x{size}, maskable={maskable})")


if __name__ == "__main__":
    main()
