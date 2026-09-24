#!/usr/bin/env python3
"""
Convert an avatar portrait into a dithered holographic vector matrix for dark.svg and light.svg.

Features:
- Crops to bust portrait (head & shoulders / upper chest), omitting hands/lower torso.
- Adds generous headroom padding so the head never touches the top header overlay.
- Alpha transparency support for cutout PNGs.
- Automatic contrast & unsharp mask enhancement for crisp dither dots.
- 1-bit Floyd-Steinberg error diffusion dithering.
- Dark-theme (highlight matrix) and Light-theme (shadow/ink matrix) support.
- 60-group interleaved holographic shimmer animation with cubic-bezier splines.
- In-place updating of dark.svg and light.svg.

Usage:
    python3 .github/scripts/convert_avatar.py profile.png
    python3 .github/scripts/convert_avatar.py --update profile.png
"""
import sys
import os
import re
import random
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

def process_avatar_image(img_path, target_w=290, target_h=320):
    if not os.path.exists(img_path):
        print(f"Error: file not found: {img_path}")
        sys.exit(1)

    src = Image.open(img_path)
    has_alpha = src.mode in ('RGBA', 'LA') or (src.mode == 'P' and 'transparency' in src.info)
    
    if has_alpha:
        src = src.convert('RGBA')
    else:
        src = src.convert('RGBA')

    orig_w, orig_h = src.size

    # Add padding above hair (80px headroom)
    canvas = Image.new('RGBA', (orig_w, orig_h + 100), (0, 0, 0, 0))
    canvas.paste(src, (0, 80))

    # Bust crop: head and upper torso (chest & shoulders), omitting lap/hands
    crop_cx = 655  # head horizontal center
    crop_w = 900
    crop_y0 = 10   # headroom above hair
    crop_h = 920   # down to upper chest

    bust = canvas.crop((int(crop_cx - crop_w / 2), crop_y0, int(crop_cx + crop_w / 2), crop_y0 + crop_h))
    bust_resized = bust.resize((target_w, target_h), Image.Resampling.LANCZOS)

    r, g, b, a = bust_resized.split()
    rgb = Image.merge('RGB', (r, g, b))

    # Grayscale and enhancements
    gray = ImageOps.grayscale(rgb)
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    gray = ImageEnhance.Contrast(gray).enhance(1.25)

    # Dark mode: subject on black background, highlights become dots (val=255)
    dark_base = Image.new('L', bust_resized.size, 0)
    dark_base.paste(gray, mask=a)
    dither_dark = dark_base.convert('1')

    # Light mode: subject on white background, shadows become dots (val=0)
    light_base = Image.new('L', bust_resized.size, 255)
    light_base.paste(gray, mask=a)
    dither_light = light_base.convert('1')

    return dither_dark, dither_light

def extract_runs(dither_img, target_val):
    w, h = dither_img.size
    pixels = dither_img.load()
    runs = []
    for y in range(h):
        start = None
        for x in range(w):
            v = pixels[x, y]
            if v == target_val:
                if start is None:
                    start = x
            else:
                if start is not None:
                    runs.append(f"M{start} {y}h{x - start}v1h-{x - start}z")
                    start = None
        if start is not None:
            runs.append(f"M{start} {y}h{w - start}v1h-{w - start}z")
    return runs

def build_shimmer_xml(runs, num_groups=60, seed=42):
    rnd = random.Random(seed)
    shuffled = list(runs)
    rnd.shuffle(shuffled)

    groups = [[] for _ in range(num_groups)]
    for i, r in enumerate(shuffled):
        groups[i % num_groups].append(r)

    lines = []
    for i in range(num_groups):
        begin_t = f"{0.20 + i * (2.0 / num_groups):.2f}s"
        p_str = "".join(groups[i])
        lines.append(
            f'      <g opacity="0">\n'
            f'        <animate attributeName="opacity" values="0;1" dur="0.9s" begin="{begin_t}" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".4 0 .2 1"/>\n'
            f'        <path d="{p_str}"/>\n'
            f'      </g>'
        )
    return "\n" + "\n".join(lines) + "\n    "

def update_svg(svg_path, shimmer_xml, fill_color, transform_str='translate(74, 134) scale(1.12)'):
    if not os.path.exists(svg_path):
        print(f"Warning: {svg_path} not found.")
        return False
    with open(svg_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r'(<g transform=")[^"]*(" fill=")[^"]*(" shape-rendering="crispEdges">).*?(</g>\s*<rect x="48" y="94")'
    if not re.search(pattern, content, re.DOTALL):
        print(f"Warning: avatar insertion anchor not found in {svg_path}.")
        return False

    replacement = rf'\g<1>{transform_str}\g<2>{fill_color}\g<3>{shimmer_xml}\g<4>'
    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"Updated {svg_path} successfully.")
    return True

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_update = "--update" in sys.argv or len(args) > 0

    if not args:
        print("Usage: python3 convert_avatar.py [--update] <path_to_image>")
        sys.exit(1)

    img_path = args[0]
    print(f"Processing bust avatar from: {img_path}...")
    dither_dark, dither_light = process_avatar_image(img_path)

    dark_runs = extract_runs(dither_dark, target_val=255)
    light_runs = extract_runs(dither_light, target_val=0)
    print(f"Extracted {len(dark_runs)} dark-mode highlight runs, {len(light_runs)} light-mode ink runs.")

    dark_xml = build_shimmer_xml(dark_runs)
    light_xml = build_shimmer_xml(light_runs)

    if do_update:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        update_svg(os.path.join(repo_root, "dark.svg"), dark_xml, fill_color="#A78BFA")
        update_svg(os.path.join(repo_root, "light.svg"), light_xml, fill_color="#312E81")

if __name__ == "__main__":
    main()
