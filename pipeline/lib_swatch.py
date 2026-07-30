"""Locating and cropping bead swatches on catalogue colour-chart pages.

Two page families need different anchors:

* structured pages keep each swatch as its own embedded raster, so the PDF
  reports an exact placement rectangle;
* flattened pages are a single full-page raster, so a swatch has to be located
  relative to its printed colour number and then trimmed to the artwork.

Both end up rendered from the page at print resolution, so the output is
identical in kind.
"""

from __future__ import annotations

import re

import fitz
import numpy as np
from PIL import Image

# A printed colour label is an optional product-line prefix, an optional size
# word, the colour number, and the tone/finish suffix letters documented in the
# legend on catalogue page 7 (L A B C D H, F for つや消し, M, S, U).
#
# The prefix names the bead line (CR = スリーカット, CHS = シャーロット特小,
# M = マガ玉, A = アンティーク, α = ミックス …) while the number itself is shared
# across lines, which is what lets one colour be shown with all the shapes it
# comes in.
LINE_PREFIXES = ("WCR", "CRLL", "CRS", "CHS", "CRD", "CR", "CH", "TB", "BM", "PF", "DEMI", "M", "A", "α", "Q")
SIZE_WORDS = ("特小", "丸小", "丸中", "丸大", "特大", "六角特小", "六角小", "六角大")

# Suffix letters are drawn from the legend only: L A B C D H mark the tone
# gradation, F is つや消し, M/FM the matte variants, S the silver-lined series and
# U the double-cut series. Restricting to this set rejects OCR noise such as the
# "9iz" and "99DDp" that dense pages otherwise produce.
SUFFIX_CHARS = "ABCDFHLMSU"

LABEL_RE = re.compile(
    r"^(?P<size>%s)?\s*(?P<prefix>%s)?[-\s]?(?P<pf>PF)?[-\s]?(?P<num>\d{1,4})(?P<suffix>[%s]{0,3})$"
    % ("|".join(SIZE_WORDS), "|".join(LINE_PREFIXES), SUFFIX_CHARS)
)

# Tokens shaped like a colour number that are actually page furniture.
NOT_A_COLOR = {"2021", "1M", "0", "4964291"}

# Bead dimensions ("4mm", "特大5.5mm") share the colour-number shape once the
# unit is upper-cased, so they are excluded before parsing.
DIMENSION_RE = re.compile(r"\d\s*(?:MM|CM|M|G|KG)$")

# Vision confuses these glyphs, but only ever inside a run of digits. The
# repairs are tried in order and the first one that yields a usable label wins,
# so a legitimate suffix letter (the L of "3L") is never rewritten.
DIGIT_REPAIRS = (
    {"l": "1", "I": "1", "i": "1", "O": "0", "o": "0"},
    {"l": "1", "I": "1", "i": "1", "O": "0", "o": "0", "L": "1", "S": "5"},
)

# The ミックスビーズ prefix α is regularly read as a zero or a capital O.
ALPHA_PREFIX_RE = re.compile(r"^[0O](?=-\d{4}$)")


class ColorLabel(dict):
    """Parsed colour label: raw text, line prefix, number, suffix letters."""

    @property
    def key(self) -> str:
        """Catalogue-wide colour number, e.g. "162C" — prefix and size dropped."""
        return "%d%s" % (self["number"], self["suffix"])


def parse_color_label(text: str) -> ColorLabel | None:
    t = text.strip().replace("．", "").replace("　", "")
    if not t:
        return None
    t = t.upper().replace("Α", "α")
    t = ALPHA_PREFIX_RE.sub("α", t)
    if t in NOT_A_COLOR or DIMENSION_RE.search(t):
        return None

    # Repairs turn letters into digits, so they may only run on a token that is
    # already mostly a number — otherwise a lone suffix letter such as "S" would
    # be "repaired" into colour 5.
    repairs = DIGIT_REPAIRS if any(ch.isdigit() for ch in t) else ()
    for repair in (None, *repairs):
        cand = t if repair is None else t.translate(str.maketrans(repair))
        m = LABEL_RE.match(cand)
        if not m:
            continue
        num = int(m.group("num"))
        if num == 0:
            continue
        prefix = m.group("prefix")
        if m.group("pf"):
            prefix = "%s PF" % prefix if prefix else "PF"
        return ColorLabel(
            raw=text.strip(),
            size=m.group("size") or None,
            prefix=prefix,
            number=num,
            suffix=m.group("suffix") or "",
        )
    return None


def parse_color_label_loose(text: str) -> ColorLabel | None:
    """As parse_color_label, but also accepts a label embedded in a caption.

    Some product pages set the whole caption as one line — "マガ玉ビーズ 5mm M171"
    — so the colour code is the last token rather than the entire string.
    """
    label = parse_color_label(text)
    if label:
        return label
    # Only a caption, not a sentence — otherwise the "＜例＞ α-3201" in a page's
    # ordering instructions would register as a product.
    t = text.strip()
    parts = t.split()
    if 1 < len(parts) <= 4 and len(t) <= 24:
        return parse_color_label(parts[-1])
    return None


def looks_like_color_no(text: str) -> str | None:
    """Catalogue colour number for an OCR token, or None."""
    label = parse_color_label(text)
    return label.key if label else None


def swatch_rects(page: fitz.Page) -> list[fitz.Rect]:
    """Embedded swatch placements, ignoring any full-page background raster."""
    area = page.rect.width * page.rect.height
    out = []
    for info in page.get_image_info(xrefs=True):
        r = fitz.Rect(info["bbox"])
        if r.width * r.height > 0.85 * area or r.width < 4 or r.height < 4:
            continue
        out.append(r)
    return out


def is_flattened(page: fitz.Page) -> bool:
    area = page.rect.width * page.rect.height
    return any(
        (lambda r: r.width * r.height > 0.85 * area)(fitz.Rect(i["bbox"]))
        for i in page.get_image_info(xrefs=True)
    )


def columns(xs: list[float], page_width: float) -> list[float]:
    """Left edges of the chart's columns, inferred from colour-number x values."""
    tol = page_width * 0.03
    groups: list[list[float]] = []
    for x in sorted(xs):
        if groups and x - groups[-1][-1] <= tol:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [min(g) for g in groups if len(g) >= 2] or [min(xs)] if xs else []


def _to_array(pix: fitz.Pixmap) -> np.ndarray:
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return np.asarray(img).astype(np.int16)


class PageRaster:
    """A page rendered once at print resolution, cropped from many times.

    Rendering per swatch would re-decode the page's full-page CMYK raster for
    every one of the ~3,000 crops; rendering once and slicing keeps the whole
    extraction to a couple of minutes.
    """

    def __init__(self, page: fitz.Page, dpi: int = 600):
        self.page = page
        self.dpi = dpi
        pix = page.get_pixmap(dpi=dpi)
        self.arr = _to_array(pix)
        self.scale = dpi / 72.0

    def _px(self, rect: fitz.Rect) -> tuple[int, int, int, int]:
        h, w, _ = self.arr.shape
        x0 = max(0, min(w - 1, int(round(rect.x0 * self.scale))))
        y0 = max(0, min(h - 1, int(round(rect.y0 * self.scale))))
        x1 = max(x0 + 1, min(w, int(round(rect.x1 * self.scale))))
        y1 = max(y0 + 1, min(h, int(round(rect.y1 * self.scale))))
        return x0, y0, x1, y1

    def sub(self, rect: fitz.Rect) -> np.ndarray:
        x0, y0, x1, y1 = self._px(rect)
        return self.arr[y0:y1, x0:x1]

    def image(self, rect: fitz.Rect) -> Image.Image:
        return Image.fromarray(self.sub(rect).astype(np.uint8), "RGB")

    def trim(self, rect: fitz.Rect, pad_pt: float = 0.6) -> fitz.Rect | None:
        """Shrink `rect` to the artwork inside it — see trim_to_artwork."""
        arr = self.sub(rect)
        return _trim_array(arr, rect, pad_pt)

    def average_color(self, rect: fitz.Rect) -> tuple[int, int, int]:
        return _average(self.sub(rect))


def trim_to_artwork(
    page: fitz.Page, rect: fitz.Rect, dpi: int = 200, pad_pt: float = 0.6
) -> fitz.Rect | None:
    """Shrink `rect` to the bead artwork inside it.

    The cell background is taken from the rectangle's own border pixels, so this
    works on white cells and on the tinted cells used for some product lines.
    Returns None when the region holds nothing but background.
    """
    if rect.width <= 1 or rect.height <= 1:
        return None
    return _trim_array(_to_array(page.get_pixmap(dpi=dpi, clip=rect)), rect, pad_pt)


def background_color(arr: np.ndarray) -> np.ndarray:
    """The cell's background, taken as the most common colour in the region.

    Sampling the region's border instead would be thrown off by the magenta rule
    the colour charts draw around each finish group: with the rule in the sample,
    the white cell interior reads as foreground and nothing gets trimmed.
    """
    q = (arr // 16).reshape(-1, 3)
    keys = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
    vals, counts = np.unique(keys, return_counts=True)
    top = vals[counts.argmax()]
    return np.array([top // 1024, (top // 32) % 32, top % 32]) * 16 + 8


def _trim_array(arr: np.ndarray, rect: fitz.Rect, pad_pt: float) -> fitz.Rect | None:
    if arr.size == 0:
        return None
    h, w, _ = arr.shape
    if h < 3 or w < 3:
        return None

    bg = background_color(arr)
    dist = np.abs(arr - bg).sum(axis=2)
    mask = dist > 42
    if mask.sum() < 12:
        return None

    # A chart cell also holds a leading ●/◆ availability marker and the cell's
    # own border rule. Both are narrow and separated from the bead strip, so
    # keeping only the widest run of occupied columns drops them.
    box = _largest_blob_bbox(mask)
    if box is None:
        return None
    r0, c0, r1, c1 = box
    c0, c1 = _drop_edge_rules(mask, c0, c1, r0, r1)
    rows = np.array([r0, r1])

    sx, sy = rect.width / w, rect.height / h
    return fitz.Rect(
        max(rect.x0 + c0 * sx - pad_pt, rect.x0),
        max(rect.y0 + rows[0] * sy - pad_pt, rect.y0),
        min(rect.x0 + (c1 + 1) * sx + pad_pt, rect.x1),
        min(rect.y0 + (rows[-1] + 1) * sy + pad_pt, rect.y1),
    )


def _largest_blob_bbox(mask: np.ndarray, block: int = 4) -> tuple[int, int, int, int] | None:
    """Bounding box of the biggest connected object in `mask`.

    The bead strip is one object; the ● / ■ / ★ availability markers, the cell
    rule and the neighbouring cell's overspill are separate ones. Picking the
    largest by area isolates the beads, which a projection onto the x-axis cannot
    do — markers sitting above and below the strip leave no gap in that
    projection even though they are plainly detached.

    Labelling runs on a `block`-downsampled copy, which is both fast enough to do
    for every cell and immune to single-pixel bridges between objects.
    """
    h, w = mask.shape
    dh, dw = h // block or 1, w // block or 1
    small = mask[: dh * block, : dw * block].reshape(dh, block, dw, block).any(axis=(1, 3))
    if not small.any():
        return None

    labels = np.where(small, np.arange(small.size).reshape(small.shape) + 1, 0)
    while True:
        prev = labels
        grown = labels.copy()
        grown[1:, :] = np.maximum(grown[1:, :], labels[:-1, :])
        grown[:-1, :] = np.maximum(grown[:-1, :], labels[1:, :])
        grown[:, 1:] = np.maximum(grown[:, 1:], labels[:, :-1])
        grown[:, :-1] = np.maximum(grown[:, :-1], labels[:, 1:])
        labels = np.where(small, grown, 0)
        if np.array_equal(labels, prev):
            break

    ids, counts = np.unique(labels[small], return_counts=True)
    winner = ids[counts.argmax()]
    rows, cols = np.where(labels == winner)
    # Back to full-resolution coordinates, then tightened against the real mask.
    r0, r1 = rows.min() * block, min((rows.max() + 1) * block, h) - 1
    c0, c1 = cols.min() * block, min((cols.max() + 1) * block, w) - 1
    sub = mask[r0 : r1 + 1, c0 : c1 + 1]
    rr = np.where(sub.any(axis=1))[0]
    cc = np.where(sub.any(axis=0))[0]
    return r0 + rr[0], c0 + cc[0], r0 + rr[-1], c0 + cc[-1]


def _artwork_span(occupied: np.ndarray) -> tuple[int | None, int | None]:
    """Span of the bead artwork within a region.

    A strip of beads is not one solid run — the gaps between individual beads
    break it into a dozen short runs, so "keep the widest run" would keep a
    single bead. Instead the runs are clustered: neighbours closer than a small
    gap belong to the same object, and the cluster holding the most ink is the
    artwork. That drops the ● availability marker and the magenta rule the charts
    draw around each finish group, both of which sit alone across a wide gap.
    """
    runs: list[tuple[int, int]] = []
    start = None
    for i, v in enumerate(occupied):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(occupied) - 1))
    if not runs:
        return None, None

    gap = max(6, int(len(occupied) * 0.04))
    clusters: list[list[tuple[int, int]]] = [[runs[0]]]
    for r in runs[1:]:
        if r[0] - clusters[-1][-1][1] - 1 <= gap:
            clusters[-1].append(r)
        else:
            clusters.append([r])

    best = max(clusters, key=lambda cl: sum(r[1] - r[0] + 1 for r in cl))
    return best[0][0], best[-1][1]


def average_color(page: fitz.Page, rect: fitz.Rect, dpi: int = 150) -> tuple[int, int, int]:
    """Mean colour of a swatch, ignoring the lightest and darkest deciles so
    specular highlights and outline shadows do not wash the value out."""
    return _average(_to_array(page.get_pixmap(dpi=dpi, clip=rect)))


def _drop_edge_rules(
    mask: np.ndarray, c0: int, c1: int, r0: int, r1: int
) -> tuple[int, int]:
    """Peel a cell rule off the edge of an artwork span.

    The rule is a hairline that runs the full height of the cell, so within the
    bead band its column is completely filled — while a bead's own columns are
    only partly filled, because the strip is rounded top and bottom. Edges that
    are completely filled are therefore the rule, not the beads.
    """
    frac = mask[r0 : r1 + 1, c0 : c1 + 1].mean(axis=0)
    if frac.size < 5:
        return c0, c1
    typical = float(np.median(frac))
    if typical >= 0.85:
        return c0, c1

    lo, hi = 0, frac.size - 1
    while lo < hi and frac[lo] >= 0.92:
        lo += 1
    while hi > lo and frac[hi] >= 0.92:
        hi -= 1
    return c0 + lo, c0 + hi


def _average(arr: np.ndarray) -> tuple[int, int, int]:
    """Representative colour of a swatch.

    A bead strip is printed on the cell's background, and the gaps between beads
    plus the trim margin mean most pixels in the crop are that background — a
    plain mean turns a near-black 玉虫 bead into mid grey. So background-coloured
    pixels are removed first, then the specular highlights and the dark bead
    outlines, and the median of what remains is the bead's own colour.

    On the round product photos the beads fill the frame, so almost nothing is
    dropped as background; the low-coverage fallback keeps those intact.
    """
    if arr.size == 0:
        return (0, 0, 0)
    h, w, _ = arr.shape
    flat = arr.reshape(-1, 3)

    keep = flat
    if h >= 3 and w >= 3:
        bg = background_color(arr)
        mask = (np.abs(arr - bg).sum(axis=2) > 42).reshape(-1)
        if mask.mean() >= 0.15:
            keep = flat[mask]

    lum = keep.sum(axis=1)
    lo, hi = np.percentile(lum, [10, 85])
    core = keep[(lum >= lo) & (lum <= hi)]
    if core.size == 0:
        core = keep
    return tuple(int(v) for v in np.median(core, axis=0))
