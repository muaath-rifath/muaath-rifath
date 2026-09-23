#!/usr/bin/env python3
"""
Convert an image (PNG, JPG, etc.) into a dithered SVG matrix.
Optionally updates dark.svg and light.svg directly.

Usage:
    python3 .github/scripts/convert_avatar.py photo.jpg
"""
import sys, os, re
from PIL import Image, ImageOps

def image_to_svg_paths(img_path, width=280, height=320):
    if not os.path.exists(img_path):
        print(f"Error: file not found: {img_path}")
        sys.exit(1)
        
    img = Image.open(img_path).convert("L")
    img = ImageOps.fit(img, (width, height), Image.Resampling.LANCZOS)
    img = ImageOps.autocontrast(img)
    dithered = img.convert("1")
    pixels = dithered.load()

    paths = []
    for y in range(height):
        start = None
        for x in range(width):
            if pixels[x, y] == 0:  # Dark pixel
                if start is None:
                    start = x
            else:
                if start is not None:
                    paths.append(f"M{start} {y}h{x - start}v1h-{x - start}z")
                    start = None
        if start is not None:
            paths.append(f"M{start} {y}h{width - start}v1h-{width - start}z")
    return "".join(paths)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 convert_avatar.py <path_to_image>")
        sys.exit(1)

    img_path = sys.argv[1]
    print(f"Processing {img_path}...")
    paths = image_to_svg_paths(img_path)
    print(f"Generated {len(paths)} characters of dithered SVG path data.")
    
    # Save standalone snippet
    out_snippet = "avatar_paths.svg"
    with open(out_snippet, "w") as f:
        f.write(f'<path d="{paths}"/>\n')
    print(f"Saved snippet to {out_snippet}")

if __name__ == "__main__":
    main()
