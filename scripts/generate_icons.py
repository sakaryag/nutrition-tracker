#!/usr/bin/env python3
"""
Generate Android/PWA icon sizes from a source image using Pillow.

Usage:
    python scripts/generate_icons.py --source icon-source.png

Generates into static/icons/:
    - icon-48.png, icon-72.png, icon-96.png, icon-144.png, icon-192.png, icon-512.png
    - icon-512-maskable.png (with 20% padding for safe zone)
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed.")
    print("Install with: pip install Pillow")
    sys.exit(1)

ICON_SIZES = [48, 72, 96, 144, 192, 512]
OUTPUT_DIR = Path(__file__).parent.parent / "static" / "icons"


def generate_icons(source_path):
    """Generate all icon sizes from source image."""
    source_file = Path(source_path)

    if not source_file.exists():
        print(f"ERROR: Source file not found: {source_path}")
        sys.exit(1)

    try:
        source_img = Image.open(source_file).convert("RGBA")
        print(f"Loaded source image: {source_file.name} ({source_img.size[0]}x{source_img.size[1]})")
    except Exception as e:
        print(f"ERROR: Failed to open image: {e}")
        sys.exit(1)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")

    # Generate standard icons
    for size in ICON_SIZES:
        resized = source_img.resize((size, size), Image.Resampling.LANCZOS)
        output_file = OUTPUT_DIR / f"icon-{size}.png"
        resized.save(output_file, "PNG")
        print(f"  ✓ {output_file.name}")

    # Generate maskable icon (512x512 with 20% padding for safe zone)
    maskable_size = 512
    safe_zone_size = int(maskable_size * 0.8)  # 409px content area
    padding = (maskable_size - safe_zone_size) // 2

    resized_maskable = source_img.resize((safe_zone_size, safe_zone_size), Image.Resampling.LANCZOS)
    maskable_img = Image.new("RGBA", (maskable_size, maskable_size), (0, 0, 0, 0))
    maskable_img.paste(resized_maskable, (padding, padding), resized_maskable)
    maskable_output = OUTPUT_DIR / "icon-512-maskable.png"
    maskable_img.save(maskable_output, "PNG")
    print(f"  ✓ {maskable_output.name}")

    print("\n✓ All icons generated successfully!")
    print("\nPlay Store Requirements Reminder:")
    print("  - 512x512 PNG icon (high resolution): icon-512.png")
    print("  - Feature graphic: 1024x500 PNG (banner for store listing)")
    print("  - Screenshots: minimum 2 phone (1080x1920) + 2 tablet (1440x2560)")
    print("  - Safe zone for adaptive icons: content within 409x409px (20% padding)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Android/PWA icons from source image")
    parser.add_argument("--source", required=True, help="Path to source icon image (1024x1024 PNG recommended)")

    args = parser.parse_args()
    generate_icons(args.source)
