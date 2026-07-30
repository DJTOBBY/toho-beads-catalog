"""Render a side-by-side proof sheet for one catalogue page.

Left: the printed page. Right: every colour number the pipeline extracted with
the swatch it cropped. Mis-assignments are obvious at a glance, which is the
only reliable check on an OCR-driven extraction.

Usage: python3 pipeline/verify_page.py 15 [27 53 ...]
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_pdf as L

ROW_H = 30
LABEL_W = 88
SWATCH_W = 190
PAGE_W = 620


def load_colors():
    with open(os.path.join(L.BUILD, "colors.json"), encoding="utf-8") as fh:
        return json.load(fh)


def sheet_for(pno: int, colors) -> Image.Image:
    doc = L.open_pdf()
    page = doc[pno - 1]
    pix = page.get_pixmap(dpi=150)
    left = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    left.thumbnail((PAGE_W, 4000))

    items = []
    for c in colors:
        for app in c["appearances"]:
            if app["pdfPage"] == pno:
                items.append((c, app))
    items.sort(key=lambda it: it[1]["swatch"])

    per_col = max(1, left.height // ROW_H)
    ncol = (len(items) + per_col - 1) // per_col or 1
    right_w = ncol * (LABEL_W + SWATCH_W)
    out = Image.new("RGB", (left.width + 12 + right_w, max(left.height, per_col * ROW_H)), "white")
    out.paste(left, (0, 0))
    dr = ImageDraw.Draw(out)

    for i, (c, app) in enumerate(items):
        cx = left.width + 12 + (i // per_col) * (LABEL_W + SWATCH_W)
        cy = (i % per_col) * ROW_H
        tone = "" if not c["suffix"] else " "
        dr.text((cx + 4, cy + 4), "%s%s" % (app["printedAs"], tone), fill="black")
        fin = c["finishes"][0]["variation"] if c["finishes"] else "—"
        dr.text((cx + 4, cy + 16), fin[:11], fill="#888")
        r, g, b = app["avgColor"]
        dr.rectangle([cx + LABEL_W - 14, cy + 4, cx + LABEL_W - 2, cy + 24], fill=(r, g, b))
        path = os.path.join(L.BUILD, "swatches", app["swatch"])
        if os.path.exists(path):
            im = Image.open(path).convert("RGB")
            im.thumbnail((SWATCH_W - 8, ROW_H - 6))
            out.paste(im, (cx + LABEL_W, cy + 3))
        dr.line([cx, cy + ROW_H - 1, cx + LABEL_W + SWATCH_W, cy + ROW_H - 1], fill="#eee")
    return out


def main():
    pages = [int(a) for a in sys.argv[1:]] or [15]
    colors = load_colors()
    os.makedirs(os.path.join(L.BUILD, "verify"), exist_ok=True)
    for pno in pages:
        img = sheet_for(pno, colors)
        path = os.path.join(L.BUILD, "verify", "p%02d.png" % pno)
        img.save(path)
        print(path, img.size)


if __name__ == "__main__":
    main()
