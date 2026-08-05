"""Render the catalogue's own pages, so a P.8 reference can be opened.

Everything else in this pipeline pulls the catalogue apart — one colour, one
swatch, one price at a time. This puts the page back: the printed layout groups
colours in a way the database cannot reproduce, and a reader who has found a
colour often wants to see what was printed around it.

Only the numbered catalogue pages are rendered; the front matter has no page
number to link to.

    python3 pipeline/render_pages.py
"""

from __future__ import annotations

import os
import sys

import fitz
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_pdf as L

PUBLIC = os.path.join(L.REPO, "public", "pages")

# Wide enough that the printed colour numbers and prices stay legible when the
# page is opened full-screen, which is the whole point of showing it.
WIDTH = 1600
QUALITY = 82


def render(doc: fitz.Document, catalog_page: int) -> int:
    page = doc[catalog_page + L.PAGE_OFFSET - 1]
    zoom = WIDTH / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    dst = os.path.join(PUBLIC, f"p{catalog_page}.webp")
    im.save(dst, "WEBP", quality=QUALITY, method=6)
    return os.path.getsize(dst)


def main() -> None:
    os.makedirs(PUBLIC, exist_ok=True)
    doc = L.open_pdf()
    last = doc.page_count - L.PAGE_OFFSET
    total = 0
    for n in range(1, last + 1):
        total += render(doc, n)
        if n % 10 == 0 or n == last:
            print(f"  P.{n:<3} … {total / 1024 / 1024:5.1f} MB")
    print(f"\n{last} ページ -> {PUBLIC}  ({total / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
