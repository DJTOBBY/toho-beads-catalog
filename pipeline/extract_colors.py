"""Build the colour dataset: one record per catalogue colour number, with the
bead lines it appears in and a cropped swatch image for each appearance.

Run after extract_finishes.py — the finish table is used to validate colour
numbers, which is what resolves OCR ambiguities the page alone cannot (a printed
"81" read as "8L" is only decidable against the list of colours that exist).

Outputs:
  build/colors.json          colour records + per-appearance metadata
  build/swatches/*.webp      cropped swatch artwork
  build/colors_report.json   coverage and validation report
"""

from __future__ import annotations

import json
import os
import re
import sys

import fitz
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_pdf as L
import lib_swatch as S
from page_map import CHART_PAGES

SWATCH_DPI = 600
# Rendered at print resolution, then capped at a size the app can serve.
SWATCH_MAX_PX = 480
PRICE_RE = re.compile(r"^([\d,]+)\s*円$")
CODE_RE = re.compile(r"^\d{6}$")
JAN_RE = re.compile(r"^4964291[-\s]?\d{6}$")
QTY_RE = re.compile(r"^(?:約)?[\d.,]+\s*(?:g|kg|m|本|粒|パック|束)")
STYLE_WORDS = ("Aiko", "AIKO", "Treasure", "クィーン", "バラ", "糸通し", "丸小", "丸中", "丸大", "特小", "特大")


def number_column_labels(blocks, page_width):
    """Colour labels that sit where a cell's number is printed.

    Labels are found by pattern, then filtered by position: the chart prints
    them flush to the left of each column, so anything further into the cell is
    stray text that happens to look like a number.
    """
    cands = []
    for b in blocks:
        label = S.parse_color_label(b.text)
        if label and b.conf >= 0.25:
            cands.append((b, label))
    if not cands:
        return []

    cols = S.columns([b.x0 for b, _ in cands], page_width)
    if not cols:
        return []
    reach = max(page_width * 0.045, 26.0)
    kept = []
    for b, label in cands:
        near = [c for c in cols if -4 <= b.x0 - c <= reach]
        if near:
            kept.append((b, label, max(near)))
    return kept, cols


def chart_cells(page, blocks, raster):
    """(label_block, label, swatch_rect, trimmed) for a flattened colour chart.

    Charts place the bead artwork either to the right of its colour number
    (丸小・丸大, Aiko, …) or directly above it (シャーロット, スリーカット, the
    photo grids). Rather than declaring which per page — some pages do both —
    each cell tries both regions and keeps the one that holds artwork instead of
    the neighbouring type.
    """
    found = number_column_labels(blocks, page.rect.width)
    if not found:
        return []
    kept, cols = found
    right_margin = page.rect.width - 14
    pitch = (cols[1] - cols[0]) if len(cols) > 1 else page.rect.width * 0.22

    # One swatch can be labelled several times — シャーロット prints "特小CHS 221"
    # and "丸小CH 221" under a single photo — so consecutive labels sharing a
    # colour number are one cell, anchored on the topmost line.
    by_col: dict[float, list] = {}
    for item in kept:
        by_col.setdefault(item[2], []).append(item)

    cells_in: list[tuple] = []
    ceiling: dict[int, float] = {}
    for col, items in by_col.items():
        items.sort(key=lambda it: it[0].y0)
        groups: list[list[tuple]] = []
        for it in items:
            prev = groups[-1][-1] if groups else None
            same = (
                prev is not None
                and prev[1].key == it[1].key
                and it[0].y0 - prev[0].y1 <= max(6.0, (it[0].y1 - it[0].y0) * 1.6)
            )
            if same:
                groups[-1].append(it)
            else:
                groups.append([it])
        for gi, group in enumerate(groups):
            anchor = group[0]
            ceiling[id(anchor[0])] = groups[gi - 1][-1][0].y1 + 2.0 if gi else 0.0
            forms = [it[1]["raw"] for it in group]
            cells_in.append((*anchor, forms))

    out = []
    for b, label, col, forms in cells_in:
        nxt = [c for c in cols if c > col + 8]
        right = (min(nxt) - 3) if nxt else right_margin

        candidates = []
        if right - b.x1 >= 8:
            candidates.append(fitz.Rect(b.x1 + 1.5, b.y0 - 3.5, right, b.y1 + 3.5))
        top = max(ceiling[id(b)], b.y0 - pitch * 1.05)
        if b.y0 - top >= 10:
            candidates.append(fitz.Rect(col - 2, top, col + pitch - 6, b.y0 - 1.5))

        best = None
        for guess in candidates:
            rect = raster.trim(guess)
            if rect is None or rect.width < 4 or rect.height < 3:
                continue
            overlap = text_overlap(rect, blocks, b)
            # Any type in the region means the artwork is elsewhere; among clean
            # regions the larger one is the swatch rather than a stray rule.
            score = (overlap > 0.02, -rect.width * rect.height)
            if best is None or score < best[0]:
                best = (score, rect)
        if best:
            # The printed cell spans its whole column, which is wider than the
            # trimmed artwork; prices and product codes are set across that full
            # width, so they need the column bounds rather than the crop's.
            out.append(
                (b, label, best[1], forms, text_overlap(best[1], blocks, b), (col - 3, right + 2))
            )
    return out


def photo_cells(page, blocks, raster):
    """(label_block, label, swatch_rect) for pages of product photographs.

    Where the photo is its own embedded raster the PDF gives an exact rectangle,
    so each is paired with its nearest caption. On the flattened photo pages
    there are no rectangles to read, so the photo is located above its caption
    and trimmed — the same anchor-then-trim trick the strip pages use, rotated.
    """
    labels = [
        (b, lab)
        for b in blocks
        if (lab := S.parse_color_label_loose(b.text)) and b.conf >= 0.25
    ]
    if not labels:
        return []

    # A page counts as structured only if it has roughly one raster per caption;
    # a lone decorative image (as on the ミックス page) means the swatches are
    # baked into the flattened background instead.
    rects = S.swatch_rects(page)
    if len(rects) >= max(4, len(labels) * 0.5):
        out = []
        for r in rects:
            if r.width < 12 or r.height < 12:
                continue
            best, best_d = None, 1e9
            for b, lab in labels:
                dx = max(r.x0 - b.x1, b.x0 - r.x1, 0)
                dy = max(r.y0 - b.y1, b.y0 - r.y1, 0)
                # Captions sit under the photo, so prefer those.
                d = dx * 2.2 + dy + (0 if b.cy >= r.y1 else 14)
                if d < best_d:
                    best, best_d = (b, lab), d
            if best and best_d < 60:
                # The rectangle comes from the PDF itself, so it is the swatch by
                # definition — captions printed over a photo are not a defect.
                cell_x = (min(r.x0, best[0].x0) - 4, max(r.x1, best[0].x1) + 4)
                out.append((best[0], best[1], r, [best[1]["raw"]], 0.0, cell_x))
        return out

    return []


def text_overlap(rect, blocks, skip) -> float:
    """Fraction of `rect` covered by OCR text other than `skip`.

    A swatch rectangle should contain artwork, not type. When the layout guess is
    wrong — looking right of the colour number on a page that prints the strip
    above it — the crop lands on the neighbouring labels instead, and this
    measures exactly that.
    """
    area = max(rect.width * rect.height, 1e-6)
    covered = 0.0
    for b in blocks:
        if b is skip:
            continue
        w = min(rect.x1, b.x1) - max(rect.x0, b.x0)
        h = min(rect.y1, b.y1) - max(rect.y0, b.y0)
        if w > 0 and h > 0:
            covered += w * h
    return min(covered / area, 1.0)


def mean_overlap(cells) -> float:
    """Mean text contamination over a cell set — a page's extraction quality."""
    if not cells:
        return 0.0
    return sum(cell[4] for cell in cells) / len(cells)


def detail_tokens(blocks):
    """Every price / product code / quantity / style token printed on the page,
    each with the x-position it occupies.

    Vision returns a printed line either as one block ("丸小 約6.5g入 180円
    741911") or as one block per field, so blocks are split into tokens and each
    token's x-range is interpolated from its offset within the block. Working at
    token level rather than block level is what lets a line be attributed to a
    cell by position.
    """
    out = []
    for b in blocks:
        text = re.sub(r"(?<=[\d,])\s+(?=円)", "", b.text)
        if not text.strip():
            continue
        span = max(b.x1 - b.x0, 1e-6)
        n = max(len(text), 1)
        pos = 0
        for raw in text.split(" "):
            if raw:
                x0 = b.x0 + span * pos / n
                x1 = b.x0 + span * (pos + len(raw)) / n
                kind, value = classify_token(raw)
                if kind:
                    out.append((kind, value, x0, x1, b.cy, b.y0, b.y1))
            pos += len(raw) + 1
    return out


def classify_token(t: str):
    if m := PRICE_RE.match(t):
        return "price", int(m.group(1).replace(",", ""))
    if CODE_RE.match(t):
        return "productCode", t
    if JAN_RE.match(t):
        return "jan", re.sub(r"[-\s]", "", t)
    if QTY_RE.match(t):
        return "quantity", t
    if any(w in t for w in STYLE_WORDS) and not any(c.isdigit() for c in t):
        return "style", t
    return None, None


def assign_details(cells, tokens):
    """Attach each detail token to the cell it is printed under.

    Returns (assigned, orphans); an orphan is a price or code with no cell above
    it, which means the colour number for that cell was never recognised.

    Earlier versions grew a rectangle outwards from each cell, which broke on the
    シャーロット pages: OCR splits "特小CHS 221" so the inferred column lands on the
    number and the codes beneath the prefix fall outside, while widening the
    rectangle far enough to reach them also reaches the next column. Choosing the
    nearest cell instead needs no rectangle — a token goes to whichever cell's
    artwork-and-label box it sits closest to, which is unambiguous even when the
    columns are offset.
    """
    boxes = []
    for block, _label, rect, _forms, _ov, _cx in cells:
        boxes.append(
            (
                min(rect.x0, block.x0),
                max(rect.x1, block.x1),
                min(rect.y0, block.y0),
                max(rect.y1, block.y1),
            )
        )

    assigned: dict[int, list] = {}
    orphans: list = []
    for kind, value, tx0, tx1, tcy, ty0, ty1 in tokens:
        best, best_d = None, 1e9
        for i, (bx0, bx1, by0, by1) in enumerate(boxes):
            # A detail line sits below its cell's label, never above it.
            if tcy < by0 - 2 or tcy > by1 + 34:
                continue
            dx = max(bx0 - tx1, tx0 - bx1, 0.0)
            dy = max(by0 - tcy, tcy - by1, 0.0)
            d = dx * 1.8 + dy
            if d < best_d:
                best, best_d = i, d
        if best is not None and best_d < 40:
            assigned.setdefault(best, []).append((kind, value, tx0, tcy))
        elif kind in ("price", "productCode", "quantity", "style"):
            orphans.append((kind, value, tx0, tx1, tcy, ty0, ty1))
    return assigned, orphans


def recover_missing_labels(page, raster, orphans, cols, pitch, tmp_dir):
    """Find colour numbers Vision missed, by re-reading just where they belong.

    A one- or two-digit colour number set in small type is the weakest thing on
    these pages for OCR: on the Aiko chart the whole row — "Aiko 370円 800014" —
    is read correctly while the "1" labelling it is not, which orphans the row.
    Rather than guess the number from its neighbours, the label's own area is
    re-rendered on its own at high resolution and read again; in isolation it is
    an easy read, and a wrong guess is impossible because nothing is inferred.

    Returns [(label, label_rect)] for the numbers recovered.
    """
    if not orphans:
        return []

    # Orphan tokens that sit on consecutive lines in the same place belong to one
    # cell, so group them before looking for a single label above the group.
    groups: list[list] = []
    for tok in sorted(orphans, key=lambda t: (round(t[2] / 30), t[4])):
        if groups:
            prev = groups[-1][-1]
            if abs(tok[2] - prev[2]) < 34 and 0 <= tok[4] - prev[4] < 22:
                groups[-1].append(tok)
                continue
        groups.append([tok])

    found = []
    tried: set[tuple[int, int]] = set()
    for gi, group in enumerate(groups):
        gx0 = min(t[2] for t in group)
        gy0 = min(t[5] for t in group)
        # The number is printed above the group, flush with its column.
        col = max([c for c in cols if c <= gx0 + 6], default=gx0)
        probe = fitz.Rect(col - 5, gy0 - 17, col + min(pitch * 0.55, 60), gy0 - 0.5)
        if probe.width < 6 or probe.height < 5:
            continue
        # One cell's orphaned lines can split into several groups; probing the
        # same spot twice would add the same colour twice.
        spot = (round(probe.x0), round(probe.y0))
        if spot in tried:
            continue
        tried.add(spot)

        path = os.path.join(tmp_dir, "probe-%d.png" % gi)
        pix = page.get_pixmap(dpi=900, clip=probe)
        pix.save(path)
        try:
            blocks = L.run_ocr_binary(path)
        except Exception:
            continue
        finally:
            if os.path.exists(path):
                os.remove(path)

        best = None
        for b in blocks:
            label = S.parse_color_label(b["t"])
            if label and b["conf"] >= 0.3:
                if best is None or b["conf"] > best[1]:
                    best = (label, b["conf"])
        if best:
            found.append((best[0], probe))

    # The same cell can be probed from two different column guesses; keep one
    # entry per colour per row.
    seen: set[tuple[str, int]] = set()
    unique = []
    for label, probe in found:
        mark = (label.key, round(probe.y0 / 4))
        if mark in seen:
            continue
        seen.add(mark)
        unique.append((label, probe))
    return unique


def variants_from(tokens_for_cell):
    """Group a cell's tokens into printed lines, one variant per line."""
    lines: list[list] = []
    for tok in sorted(tokens_for_cell, key=lambda t: (t[3], t[2])):
        # Printed lines in a cell are ~8pt apart, so a slightly generous tolerance
        # keeps a price and its product code together when OCR reports their
        # baselines a shade apart.
        if lines and abs(tok[3] - lines[-1][0][3]) <= 4.5:
            lines[-1].append(tok)
        else:
            lines.append([tok])

    variants, jans = [], []
    for line in lines:
        v: dict = {}
        for kind, value, _x, _y in sorted(line, key=lambda t: t[2]):
            if kind == "jan":
                jans.append(value)
            else:
                v[kind] = value
        if "price" in v or "productCode" in v:
            variants.append(v)

    # Some charts set one price across two size rows — "丸小 074798 / 100円 /
    # 丸大 075153" — which reads as a bare price between two bare codes. Fold that
    # shared price back into the rows it covers.
    loose = [v for v in variants if "price" in v and "productCode" not in v]
    priced = [v for v in variants if "productCode" in v and "price" not in v]
    if len(loose) == 1 and priced:
        for v in priced:
            v["price"] = loose[0]["price"]
        variants = [v for v in variants if v is not loose[0]]
    return variants, jans


# Colour numbers the finish table itself has wrong. Each was confirmed by
# zooming the printed page and by the number appearing correctly elsewhere in
# the catalogue.
FINISH_TABLE_FIXES = {"1660": "166C"}


def known_color_keys() -> dict[str, list[dict]]:
    """colour number -> the finish variations that list it.

    Table entries go through the same label parser as the chart pages so that
    both sides agree on a key: the table prints the 蓄光 colours as "PF2700S"
    while the chart prints "2700S", and only one of those can be the key.
    """
    path = os.path.join(L.BUILD, "finishes.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    index: dict[str, list[dict]] = {}
    for finish in data["finishes"]:
        for var in finish["variations"]:
            for code in var["colorNumbers"]:
                code = FINISH_TABLE_FIXES.get(code, code)
                label = S.parse_color_label(code)
                index.setdefault(label.key if label else code, []).append(
                    {"finish": finish["name"], "variation": var["name"], "methods": var["methods"]}
                )
    return index


def reconcile(label: S.ColorLabel, known: dict) -> tuple[str, str | None, str | None]:
    """Return (colour key, base key for finish lookup, correction note).

    The finish table lists the glossy base of each colour. つや消し versions carry
    an extra F (and FM for the strong matte of a 着色 or パール colour) which the
    table does not repeat, so an unmatched key is retried without that tail — the
    matte colour then inherits the base colour's finish.

    A key that still does not exist is more likely a misread, and the letters
    Vision confuses with digits are L/S/B/D, so a digit reading is tried last.
    """
    key = label.key
    if key in known:
        return key, key, None

    suffix = label["suffix"]
    for tail in ("FM", "F"):
        if suffix.endswith(tail):
            base = "%d%s" % (label["number"], suffix[: -len(tail)])
            if base in known:
                return key, base, None

    if suffix:
        swapped = {"L": "1", "S": "5", "B": "8", "D": "0"}
        if all(c in swapped for c in suffix):
            alt = "%d%s" % (label["number"], "".join(swapped[c] for c in suffix))
            if alt in known:
                return alt, alt, "%s→%s (接尾文字を数字として再解釈)" % (key, alt)
    return key, key, None


def main():
    doc = L.open_pdf()
    known = known_color_keys()
    tmp_dir = os.path.join(L.BUILD, "probe")
    os.makedirs(tmp_dir, exist_ok=True)
    # Filenames encode cell positions, so a re-run with changed geometry would
    # otherwise leave orphans behind.
    import shutil
    shutil.rmtree(os.path.join(L.BUILD, "swatches"), ignore_errors=True)
    os.makedirs(os.path.join(L.BUILD, "swatches"), exist_ok=True)

    colors: dict[str, dict] = {}
    report = {"pages": [], "unknownKeys": {}, "corrections": [], "layoutOverrides": [], "recovered": []}

    for pno in sorted(CHART_PAGES):
        meta = CHART_PAGES[pno]
        page = doc[pno - 1]
        blocks = L.load_ocr(pno, page)
        raster = S.PageRaster(page, dpi=SWATCH_DPI)
        # The page map records the expected layout, but which one actually holds
        # is decided by measuring: several pages print the strip above its colour
        # number rather than beside it, and a wrong guess crops the neighbouring
        # labels instead of the beads.
        # Pages whose swatches are separate embedded rasters get exact rectangles
        # from the PDF; the flattened ones are located from their colour numbers.
        embedded = photo_cells(page, blocks, raster)
        derived = chart_cells(page, blocks, raster)
        cells, layout = ((embedded, "embedded") if len(embedded) >= len(derived)
                         else (derived, "derived"))

        # Prices and product codes go to whichever cell they are printed under.
        tokens = detail_tokens(blocks)
        detail, orphans = assign_details(cells, tokens)

        # Rows left without a cell mean their colour number went unread; re-read
        # just that spot and add the cells it turns up.
        if orphans and layout == "derived":
            found = number_column_labels(blocks, page.rect.width)
            cols = found[1] if found else []
            pitch = (cols[1] - cols[0]) if len(cols) > 1 else page.rect.width * 0.22
            recovered = recover_missing_labels(page, raster, orphans, cols, pitch, tmp_dir)
            for label, probe in recovered:
                guess = fitz.Rect(probe.x1 + 1.5, probe.y0 - 2, probe.x0 + pitch - 6, probe.y1 + 3)
                rect = raster.trim(guess)
                if rect is None or rect.width < 4 or rect.height < 3:
                    continue
                anchor = L.Block(label["raw"], 1.0, probe.x0, probe.y0, probe.x1, probe.y1)
                cells.append((anchor, label, rect, [label["raw"]], text_overlap(rect, blocks, anchor),
                              (probe.x0 - 3, probe.x0 + pitch)))
                report["recovered"].append({"page": pno, "label": label["raw"]})
            if recovered:
                detail, _ = assign_details(cells, tokens)

        # Cells on a page are set to a common size, so a crop far off that size
        # swallowed something it should not have — a decorative graphic, a
        # neighbouring row. Flag those the same way as text contamination.
        if cells:
            widths = sorted(c[2].width for c in cells)
            heights = sorted(c[2].height for c in cells)
            med_w = widths[len(widths) // 2]
            med_h = heights[len(heights) // 2]
        else:
            med_w = med_h = 0.0

        n_written = 0
        seen: dict[str, int] = {}
        for cell_index, (block, label, rect, forms, overlap, cell_x) in enumerate(cells):
            # A crop far off the page's usual cell size caught something it
            # should not have: too large means a decorative graphic or a
            # neighbouring row, too thin means the trim locked onto a table rule
            # instead of the beads.
            oversized = med_w > 0 and (
                rect.width > med_w * 2.2
                or rect.height > med_h * 2.2
                or rect.height < med_h * 0.45
                or rect.width < med_w * 0.25
            )
            key, base_key, note = reconcile(label, known)
            if note:
                report["corrections"].append({"page": pno, "note": note})
            if base_key not in known:
                report["unknownKeys"].setdefault(key, []).append(
                    {"page": pno, "raw": label["raw"]}
                )

            # The same colour number can appear more than once on a page (two
            # sizes in adjacent rows), so an ordinal disambiguates the filename —
            # otherwise later cells overwrite earlier ones while every appearance
            # still points at the same file. Naming by ordinal rather than by
            # pixel position keeps URLs stable when crop geometry is adjusted.
            stem = "p%02d-%s-%s" % (pno, key, label["prefix"] or "base")
            stem = stem.replace("/", "_").replace(" ", "")
            seen[stem] = seen.get(stem, 0) + 1
            name = "%s.webp" % stem if seen[stem] == 1 else "%s-%d.webp" % (stem, seen[stem])
            out_path = os.path.join(L.BUILD, "swatches", name)
            img = raster.image(rect)
            img.thumbnail((SWATCH_MAX_PX, SWATCH_MAX_PX))
            img.save(out_path, "WEBP", quality=88, method=5)
            n_written += 1

            variants, jans = variants_from(detail.get(cell_index, []))
            rec = colors.setdefault(
                key,
                {
                    "key": key,
                    "number": label["number"],
                    "suffix": label["suffix"],
                    "matte": label["suffix"].endswith("F"),
                    "finishBase": base_key if base_key != key else None,
                    "finishes": known.get(base_key, []),
                    "appearances": [],
                },
            )
            rec["appearances"].append(
                {
                    "pdfPage": pno,
                    "catalogPage": pno - L.PAGE_OFFSET,
                    "line": meta["line"],
                    "beadTypes": meta["types"],
                    "salesStyle": meta["style"],
                    "printedAs": label["raw"],
                    "linePrefix": label["prefix"],
                    "swatch": name,
                    "avgColor": raster.average_color(rect),
                    "printedForms": forms,
                    # Type inside a swatch region means the crop missed the
                    # artwork; the app uses this to hide unreliable crops.
                    "textOverlap": round(overlap, 4),
                    "oversized": bool(oversized),
                    "variants": variants,
                    "jan": jans,
                }
            )

        report["pages"].append(
            {"pdfPage": pno, "catalogPage": pno - L.PAGE_OFFSET, "line": meta["line"],
             "layout": layout, "cells": len(cells), "swatches": n_written,
             "clean": sum(1 for c in cells if c[4] <= 0.02),
             "textOverlap": round(mean_overlap(cells), 4)}
        )
        clean = sum(1 for c in cells if c[4] <= 0.02)
        print("p%02d (cat %2d) %-26s %-8s cells=%3d clean=%3d overlap=%.3f" % (
            pno, pno - L.PAGE_OFFSET, meta["line"], layout, len(cells), clean,
            mean_overlap(cells)))

    with open(os.path.join(L.BUILD, "colors.json"), "w", encoding="utf-8") as fh:
        json.dump(sorted(colors.values(), key=lambda c: (c["number"], c["suffix"])),
                  fh, ensure_ascii=False, indent=1)
    with open(os.path.join(L.BUILD, "colors_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    total_app = sum(len(c["appearances"]) for c in colors.values())
    unknown = sum(len(v) for v in report["unknownKeys"].values())
    print()
    print("colours          : %d" % len(colors))
    print("appearances      : %d" % total_app)
    print("with finish data : %d" % sum(1 for c in colors.values() if c["finishes"]))
    print("corrections      : %d" % len(report["corrections"]))
    print("unknown keys     : %d distinct / %d occurrences" % (len(report["unknownKeys"]), unknown))
    print("recovered labels : %d" % len(report["recovered"]))


if __name__ == "__main__":
    main()
