#!/usr/bin/env python3
"""Turn a paper figure into a transparent-background PNG for img/papers/.

See tools/README.md for the full workflow. Short version:

    # from a PDF page, cropping the figure out of the page render
    ./tools/make-pub-figure.py paper.pdf img/papers/my-paper.png \
        --page 4 --dpi 600 --crop 2560,380,4900,1450

    # from an already-extracted figure image
    ./tools/make-pub-figure.py fig1.png img/papers/my-paper.png

Pipeline: render/open -> crop -> white to transparent -> trim to content.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops

# Pixels whose R, G and B are all >= this are treated as page white and made
# fully transparent. Everything else stays fully opaque, so alpha is binary.
# 240 is what the original five figures on the site were processed with.
WHITE_THRESHOLD = 240


def render_pdf_page(pdf: Path, page: int, dpi: int) -> Image.Image:
    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp) / "page"
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
             str(pdf), str(prefix)],
            check=True,
        )
        rendered = sorted(Path(tmp).glob("page*.png"))
        if not rendered:
            sys.exit(f"pdftoppm produced no output for {pdf} page {page}")
        return Image.open(rendered[0]).convert("RGB")


def whiten_to_alpha(im: Image.Image, threshold: int) -> Image.Image:
    """Make page-white transparent, leaving every other pixel fully opaque."""
    im = im.convert("RGBA")
    # A pixel is content if any channel is below the threshold, i.e. alpha is 0
    # exactly where min(R, G, B) >= threshold. Point-mapping each channel and
    # taking the max is much faster than a per-pixel Python loop.
    r, g, b, _ = im.split()
    mask = content_mask(r, threshold)
    for channel in (g, b):
        mask = ImageChops.lighter(mask, content_mask(channel, threshold))
    im.putalpha(mask)
    return im


def content_mask(channel: Image.Image, threshold: int) -> Image.Image:
    """255 where this channel is dark enough to count as content, else 0."""
    return channel.point(lambda v: 255 if v < threshold else 0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="PDF or raster image")
    ap.add_argument("output", type=Path, help="destination PNG")
    ap.add_argument("--page", type=int, default=1, help="PDF page holding the figure")
    ap.add_argument("--dpi", type=int, default=600, help="PDF render resolution")
    ap.add_argument("--crop", help="x0,y0,x1,y1 in rendered pixels, generous is fine")
    ap.add_argument("--threshold", type=int, default=WHITE_THRESHOLD,
                    help="channel value at or above which a pixel counts as white")
    ap.add_argument("--max-width", type=int, default=0,
                    help="downscale if wider than this (0 = leave alone)")
    args = ap.parse_args()

    if args.source.suffix.lower() == ".pdf":
        im = render_pdf_page(args.source, args.page, args.dpi)
    else:
        im = Image.open(args.source).convert("RGB")

    if args.crop:
        im = im.crop(tuple(int(v) for v in args.crop.split(",")))

    im = whiten_to_alpha(im, args.threshold)

    bbox = im.getchannel("A").getbbox()
    if bbox is None:
        sys.exit("crop contains no non-white content")
    im = im.crop(bbox)

    if args.max_width and im.width > args.max_width:
        height = round(im.height * args.max_width / im.width)
        im = im.resize((args.max_width, height), Image.LANCZOS)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    im.save(args.output, optimize=True)
    print(f"{args.output}: {im.width}x{im.height}")


if __name__ == "__main__":
    main()
