"""Extract the official finish taxonomy from catalogue pages 6-7 (PDF 13-14).

Those two pages carry the "ビーズの加工の種類" table: for every finish type and
variation, the complete list of colour numbers that use it. It is the
authoritative mapping, so the app classifies colours from this rather than from
per-page headings.

Output: build/finishes.json
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_pdf as L

# The pages Vision reads reliably except for a handful of glyphs. 艶 is outlined
# in a way Vision consistently reports as 砡; the rest are digit/letter mixups
# inside colour-number runs.
GLYPH_FIXES = {"砡": "艶", "自色": "白色"}

# Column x-boundaries are read from the page's own rules, but the header row and
# the table's bottom edge need naming.
FINISH_PAGES = (13, 14)

# The table footnotes each variation with a circled digit keying into the
# "ビーズの加工方法の説明" legend on catalogue page 7. Vision renders those circled
# digits inconsistently (①→"の", ③→"®", …), so they are stripped from the label
# and the method is derived from the label text instead.
# Circled digits can land anywhere in the label; "の" is only ever a stray marker
# when it sits at the end or before a bracket, so it is stripped there only.
MARKER_RE = re.compile(r"[®©™①-⑳]")
TRAILING_NO_RE = re.compile(r"の(?=$|[（(])")
METHODS = {
    "ラスター": ("ラスター", "ビーズの表面に、白色の照りを加えること。"),
    "オーロラ": ("オーロラ", "ビーズの表面に、レインボー光沢の照りを加えること。"),
    "着色": ("着色", "ビーズに塗料及び染料で色を着けたもの。"),
    "PF": ("PF", "従来の同色番に比べて、摩擦に強くなっており、色が落ちにくくなっています。"),
    "蛍光": ("蛍光", "ネオンのように鮮やかに発色する色です。"),
}

# Variation labels Vision failed to read at all, keyed by (finish, row index).
NAME_FALLBACKS = {("本金メッキ", 1): "本金メッキオーロラ"}

# Finish-type labels that lose their interpunct in the outlined original.
TYPE_FIXES = {"コゲ金銅ラスター": "コゲ金・銅ラスター"}


def norm_text(s: str) -> str:
    for a, b in GLYPH_FIXES.items():
        s = s.replace(a, b)
    return s


def table_geometry(page):
    """Return (row_bounds, group_bounds, col_x) for the finish table."""
    hs, vs = L.rules(page)
    # Verticals that run the height of the table give the column splits.
    long_v = [v for v in vs if v[2] - v[1] > 200]
    col_x = sorted({round(v[0]) for v in long_v})
    left = min(h[1] for h in hs)
    right = max(h[2] for h in hs)
    bottom = max(v[2] for v in long_v)

    # Horizontal rules spanning the variation+colour columns delimit rows;
    # those spanning the whole table also delimit finish-type groups.
    var_x = col_x[-2] if len(col_x) >= 2 else col_x[0]
    row_y, group_y = [], []
    for y, x0, x1 in hs:
        if x1 < right - 20:
            continue
        if x0 <= left + 20:
            row_y.append(y)
            group_y.append(y)
        elif x0 <= var_x + 20:
            row_y.append(y)
    row_y = sorted(set(row_y + [bottom]))
    return row_y, sorted(set(group_y + [bottom])), [left] + col_x + [right]


def cell_text(blocks, x0, x1, y0, y1, joiner=""):
    """OCR text whose centre falls inside the cell, in reading order."""
    inside = [b for b in blocks if x0 <= b.cx <= x1 and y0 <= b.cy <= y1]
    inside.sort(key=lambda b: (round(b.cy, 1), b.cx))
    return joiner.join(norm_text(b.text) for b in inside)


# Japanese prose needs no separator across a line break, but a colour-number list
# that wraps does — otherwise "…171" + "171L…" reads as the single number 171171.
LIST_WRAP = (re.compile(r"[0-9A-Za-z]$"), re.compile(r"^[0-9]"))


def prose_text(blocks, x0, x1, y0, y1) -> str:
    """Cell text joined the way the printed cell reads."""
    inside = [b for b in blocks if x0 <= b.cx <= x1 and y0 <= b.cy <= y1]
    inside.sort(key=lambda b: (round(b.cy, 1), b.cx))
    out = ""
    for b in inside:
        piece = norm_text(b.text)
        if out and LIST_WRAP[0].search(out) and LIST_WRAP[1].match(piece):
            out += "・"
        out += piece
    return out


CODE_RE = re.compile(r"^(?:PF)?\d{1,4}[A-Z]{0,3}$")


def unglue(tok: str, widths: set[int]) -> list[str] | None:
    """Split a token where the printed catalogue omitted a separating comma.

    The 2021 edition has four such typos (e.g. "1202,12031204,1205" on
    catalogue page 6). A split is only accepted when both halves are valid codes
    of the same digit width and that width also occurs among the row's other
    codes, which keeps the rule from inventing splits inside long numbers.
    """
    for i in range(1, len(tok)):
        a, b = tok[:i], tok[i:]
        if not (CODE_RE.match(a) and CODE_RE.match(b)):
            continue
        da = len(re.match(r"\D*(\d*)", a).group(1))
        db = len(re.match(r"\D*(\d*)", b).group(1))
        if da == db and da in widths:
            return [a, b]
    return None


def split_codes(raw: str) -> tuple[list[str], list[str]]:
    """Split a colour-number run into (codes, rejected_tokens).

    OCR sometimes reads the separating comma as a period or drops it entirely,
    and the trailing footnotes ("※423=941同色異品番") ride along in the same cell.
    """
    raw = raw.split("※")[0]
    raw = raw.replace("，", ",").replace("、", ",").replace("．", ",")
    raw = re.sub(r"[.\s]+", ",", raw)
    toks = [t.strip().upper() for t in raw.split(",") if t.strip()]
    # O/0 confusion only ever occurs inside a numeric run.
    toks = [re.sub(r"(?<=\d)O", "0", t) for t in toks]
    widths = {len(re.match(r"\D*(\d*)", t).group(1)) for t in toks if CODE_RE.match(t)}

    codes, bad = [], []
    for tok in toks:
        if CODE_RE.match(tok):
            codes.append(tok)
            continue
        pair = unglue(tok, widths)
        if pair:
            codes.extend(pair)
            bad.append("%s→%s (原本のカンマ抜け)" % (tok, ",".join(pair)))
        else:
            bad.append(tok)
    return codes, bad


def note_text(raw: str) -> str | None:
    parts = raw.split("※")[1:]
    return "；".join(p.strip() for p in parts) if parts else None


def clean_variation(name: str) -> tuple[str, list[str]]:
    """Strip the legend markers off a variation label and name its methods."""
    name = TRAILING_NO_RE.sub("", MARKER_RE.sub("", name)).strip()
    methods = [key for key in METHODS if key in name]
    return name, methods


def extract(doc) -> dict:
    finishes: list[dict] = []
    rejected: list[dict] = []

    for pno in FINISH_PAGES:
        page = doc[pno - 1]
        blocks = L.load_ocr(pno, page)
        row_y, group_y, cols = table_geometry(page)
        type_x = (cols[0], cols[1])
        desc_x = (cols[1], cols[2])
        var_x = (cols[2], cols[3])
        code_x = (cols[3], cols[4])

        # Group = one 加工の種類; it spans one or more variation rows.
        for gi in range(len(group_y) - 1):
            gy0, gy1 = group_y[gi], group_y[gi + 1]
            name = cell_text(blocks, *type_x, gy0, gy1)
            desc = prose_text(blocks, *desc_x, gy0, gy1)
            if not name:
                continue
            name = TYPE_FIXES.get(name, name)
            rows = [y for y in row_y if gy0 - 0.5 <= y <= gy1 + 0.5]
            variations = []
            for ri in range(len(rows) - 1):
                ry0, ry1 = rows[ri], rows[ri + 1]
                # Line wraps inside the colour column carry no trailing comma,
                # so join the OCR lines with one.
                raw = cell_text(blocks, *code_x, ry0, ry1, joiner=",")
                codes, bad = split_codes(raw)
                if not codes:
                    continue
                label = cell_text(blocks, *var_x, ry0, ry1)
                label = NAME_FALLBACKS.get((name, len(variations)), label) or name
                label, methods = clean_variation(label)
                variations.append(
                    {
                        "name": label,
                        "methods": methods,
                        "colorNumbers": codes,
                        "note": note_text(raw),
                    }
                )
                if bad:
                    rejected.append(
                        {"page": pno, "finish": name, "tokens": bad, "raw": raw}
                    )
            if variations:
                finishes.append(
                    {"name": name, "description": desc, "variations": variations}
                )

    return {"finishes": finishes, "rejected": rejected}


def main():
    doc = L.open_pdf()
    result = extract(doc)
    os.makedirs(L.BUILD, exist_ok=True)
    out = os.path.join(L.BUILD, "finishes.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)

    total = sum(len(v["colorNumbers"]) for f in result["finishes"] for v in f["variations"])
    print("finish types: %d" % len(result["finishes"]))
    print("variations  : %d" % sum(len(f["variations"]) for f in result["finishes"]))
    print("colour refs : %d" % total)
    print("rejected    : %d" % len(result["rejected"]))
    for f in result["finishes"]:
        print("  %-14s %s" % (f["name"], ", ".join(
            "%s(%d)" % (v["name"], len(v["colorNumbers"])) for v in f["variations"])))
    for r in result["rejected"]:
        print("  ! p%d %s -> %s" % (r["page"], r["finish"], r["tokens"]))
    print("wrote", out)


if __name__ == "__main__":
    main()
