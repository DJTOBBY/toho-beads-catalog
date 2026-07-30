"""Shared helpers for reading the TOHO catalogue PDF.

The catalogue is an Illustrator print original: every glyph is outlined, so no
page has a text layer. Text therefore comes from OCR (see ocr_page.swift) and
geometry comes from the PDF's own vector/raster structure.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass

import fitz

# PDF page N shows catalogue page N - PAGE_OFFSET (verified on p15/p27/p53/p77).
PAGE_OFFSET = 7

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(REPO, "build")
DEFAULT_PDF = os.path.expanduser("~/Downloads/ビーズカタログ2021-1-2部.pdf")


def pdf_path() -> str:
    return os.environ.get("TOHO_CATALOG_PDF", DEFAULT_PDF)


def open_pdf() -> fitz.Document:
    return fitz.open(pdf_path())


@dataclass
class Block:
    """One OCR text block, in PDF point coordinates."""

    text: str
    conf: float
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


def load_ocr(pno: int, page: fitz.Page) -> list[Block]:
    """OCR blocks for 1-based PDF page `pno`, scaled to the page's point box."""
    path = os.path.join(BUILD, "ocr", "p%02d.json" % pno)
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    W, H = page.rect.width, page.rect.height
    out = []
    for b in raw:
        out.append(
            Block(
                text=b["t"],
                conf=b["conf"],
                x0=b["x"] * W,
                y0=b["y"] * H,
                x1=(b["x"] + b["w"]) * W,
                y1=(b["y"] + b["h"]) * H,
            )
        )
    return out


def rules(page: fitz.Page, min_h: float = 50.0, min_v: float = 20.0):
    """Table rule lines as (horizontals, verticals).

    horizontals: list of (y, x_start, x_end); verticals: list of (x, y_start, y_end).
    Both thin filled rectangles and stroked lines are recognised, since the
    catalogue mixes the two.
    """
    hs, vs = set(), set()
    for dr in page.get_drawings():
        for item in dr["items"]:
            if item[0] == "re":
                r = item[1]
                if r.height < 2 and r.width > min_h:
                    hs.add((round(r.y0, 1), round(r.x0, 1), round(r.x1, 1)))
                if r.width < 2 and r.height > min_v:
                    vs.add((round(r.x0, 1), round(r.y0, 1), round(r.y1, 1)))
            elif item[0] == "l":
                a, b = item[1], item[2]
                if abs(a.y - b.y) < 1 and abs(a.x - b.x) > min_h:
                    hs.add((round(a.y, 1), round(min(a.x, b.x), 1), round(max(a.x, b.x), 1)))
                if abs(a.x - b.x) < 1 and abs(a.y - b.y) > min_v:
                    vs.add((round(a.x, 1), round(min(a.y, b.y), 1), round(max(a.y, b.y), 1)))
    return sorted(hs), sorted(vs)


def cluster(values: list[float], tol: float) -> list[list[float]]:
    """Group sorted-able 1-D values into runs no more than `tol` apart."""
    out: list[list[float]] = []
    for v in sorted(values):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return out


def crop(page: fitz.Page, rect, dpi: int = 600) -> fitz.Pixmap:
    """Render just `rect` of the page at `dpi` — works for both flattened and
    vector pages, so swatches come out at print resolution either way."""
    return page.get_pixmap(dpi=dpi, clip=fitz.Rect(rect))


def run_ocr_binary(image_path: str) -> list[dict]:
    binary = os.path.join(BUILD, "ocr_page")
    out = subprocess.run([binary, image_path], capture_output=True, check=True)
    return json.loads(out.stdout)
