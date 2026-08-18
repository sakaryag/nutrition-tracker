"""Generate PNG icons for PWA and Play Store from icon.svg."""
import os
import subprocess
import sys
from pathlib import Path

SIZES = [48, 72, 96, 144, 192, 512]
MASKABLE_SIZE = 512

ROOT = Path(__file__).resolve().parent.parent
SVG_PATH = ROOT / "static" / "icon.svg"
ICONS_DIR = ROOT / "static" / "icons"
ICONS_DIR.mkdir(parents=True, exist_ok=True)


def svg_to_png_via_inkscape(svg_path, out_path, size):
    """Try inkscape first."""
    try:
        subprocess.run(
            ["inkscape", str(svg_path), f"--export-width={size}", f"--export-height={size}", f"--export-filename={out_path}"],
            check=True, capture_output=True
        )
        return True
    except Exception:
        return False


def svg_to_png_via_pillow(svg_path, out_path, size):
    """Fallback: render SVG as a green square with 'N' text (placeholder)."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (size, size), (45, 122, 79, 255))  # #2D7A4F green
    draw = ImageDraw.Draw(img)
    # Draw white 'N' letter as placeholder
    font_size = int(size * 0.55)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "N", font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - w) // 2, (size - h) // 2 - bbox[1]), "N", fill="white", font=font)
    img.save(out_path, "PNG")
    return True


def generate():
    print(f"Generating icons in {ICONS_DIR}")
    for size in SIZES:
        out = ICONS_DIR / f"icon-{size}.png"
        ok = svg_to_png_via_inkscape(SVG_PATH, out, size)
        if not ok:
            ok = svg_to_png_via_pillow(SVG_PATH, out, size)
        print(f"  icon-{size}.png {'OK' if ok else 'FAILED'}")

    # Maskable icon (512x512 with padding ~10%)
    out_maskable = ICONS_DIR / "icon-512-maskable.png"
    from PIL import Image, ImageDraw, ImageFont
    base = Image.open(ICONS_DIR / "icon-512.png").convert("RGBA")
    mask = Image.new("RGBA", (512, 512), (45, 122, 79, 255))
    padding = 52  # ~10%
    inner = base.resize((512 - 2 * padding, 512 - 2 * padding), Image.LANCZOS)
    mask.paste(inner, (padding, padding), inner)
    mask.save(out_maskable, "PNG")
    print(f"  icon-512-maskable.png OK")

    print("Done.")


if __name__ == "__main__":
    generate()
