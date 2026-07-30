"""Assemble the app's data files from the extraction outputs.

Prices are deliberately kept out of the generated catalogue. They change, and
this catalogue is the 2021 edition, so they live in `data/prices.json` — a plain
file meant to be hand-edited. Re-running the pipeline regenerates the catalogue
but never overwrites that file; `--reseed` is the explicit opt-in.

Outputs:
  data/catalog.json          colours, finishes, bead types, sales styles
  data/prices.json           editable price layer (created once, then left alone)
  data/prices.seed.json      what the catalogue printed, for reference/diffing
  public/swatches/*.webp     swatch artwork the app serves
"""

from __future__ import annotations

import argparse
import colorsys
import json
import os
import shutil
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_pdf as L
from bead_types import BEAD_TYPES, SALES_STYLES
from page_map import CHART_PAGES, NON_CHART_PAGES

DATA = os.path.join(L.REPO, "data")

# Above this fraction of a swatch region covered by type, the crop landed on the
# neighbouring labels instead of the beads.
MAX_TEXT_OVERLAP = 0.02

# Cells on a page are drawn to one size, so a crop whose proportions are well off
# that page's norm is not the beads — it is a rule, a tint band or a fragment of
# the layout. The window is wide enough to leave genuine cells alone.
ASPECT_WINDOW = (0.80, 1.35)
PUBLIC_SWATCHES = os.path.join(L.REPO, "public", "swatches")
PUBLIC_OFFICIAL = os.path.join(L.REPO, "public", "official")
OFFICIAL_JSON = os.path.join(L.BUILD, "web", "official.json")
OFFICIAL_IMG = os.path.join(L.BUILD, "web", "img")

EDITION = "2021年10月時点（第1部・第2部）"
PRICE_NOTE = (
    "掲載価格は2021年カタログ時点の本体価格（定価・税抜）です。"
    "価格は変更される場合があるため、data/prices.json を編集して最新の価格に更新できます。"
)

# Hue families for the colour filter. Ranges are in degrees on the HSV wheel.
HUE_FAMILIES = [
    ("レッド", 345, 10),
    ("オレンジ", 10, 45),
    ("イエロー", 45, 70),
    ("グリーン", 70, 160),
    ("ブルー", 160, 250),
    ("パープル", 250, 290),
    ("ピンク", 290, 345),
]


def color_metrics(rgb) -> dict:
    r, g, b = (v / 255 for v in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    hue = h * 360
    family = "ニュートラル"
    if s >= 0.12:
        for name, lo, hi in HUE_FAMILIES:
            if lo <= hi:
                if lo <= hue < hi:
                    family = name
                    break
            elif hue >= lo or hue < hi:
                family = name
                break
    else:
        family = "ホワイト" if v > 0.82 else "ブラック" if v < 0.25 else "グレー"
    return {
        "hex": "#%02x%02x%02x" % tuple(rgb),
        "hue": round(hue),
        "sat": round(s, 3),
        "val": round(v, 3),
        "family": family,
    }


def tone_label(suffix: str) -> str | None:
    """The catalogue's tone gradation: 5L(淡) ← 5A, 5, 5B, 5C, 5D, 5H (濃)."""
    order = {"L": "最も淡い", "A": "淡い", "B": "やや濃い", "C": "濃い", "D": "より濃い", "H": "最も濃い"}
    letters = [c for c in suffix if c in order]
    return order[letters[0]] if letters else None


def suffix_notes(suffix: str) -> list[str]:
    out = []
    if tone := tone_label(suffix):
        out.append("色調: %s" % tone)
    if suffix.endswith("FM"):
        out.append("FM: 着色またはパールのつや消し加工（つや消しが強い）")
    elif suffix.endswith("F"):
        out.append("F: つや消し（frosted）加工")
    if "S" in suffix:
        out.append("S: 銀メッキ系の同色番")
    if "U" in suffix:
        out.append("U: ダブルスリーカット系の同色番")
    return out


THUMB = (12, 4)


def _fingerprint(swatch: str) -> list[float] | None:
    """A crop reduced to a handful of pixels, for comparing crops to each other.

    Comparing average colours alone cannot tell a bead strip from a coloured rule
    that happens to average out the same. A tiny thumbnail keeps enough of the
    layout — beads repeat across the strip, a rule is flat — to make the odd one
    out obvious.
    """
    path = os.path.join(L.BUILD, "swatches", swatch)
    if not os.path.exists(path):
        return None
    with Image.open(path) as im:
        small = im.convert("RGB").resize(THUMB, Image.BILINEAR)
    return [v for px in small.getdata() for v in px]


def consensus_color(apps: list[dict]) -> tuple[dict, dict]:
    """Pick a colour's true reading by majority vote across its appearances.

    A crop can lose colour to the cell background or, occasionally, land on a
    rule or a heading instead of the beads. Both are outliers among the several
    pages a colour is printed on, so the appearances vote: the colour is their
    per-channel median, and the swatch shown is the appearance whose *image* is
    most like its siblings — compared as thumbnails, since a mis-crop can match
    on average colour while looking nothing like the beads.
    """
    rgbs = [a["avgColor"] for a in apps]
    med = [sorted(ch)[len(ch) // 2] for ch in zip(*rgbs)]

    def colour_distance(a: dict) -> int:
        return sum(abs(x - y) for x, y in zip(a["avgColor"], med))

    rep = None
    if len(apps) >= 3:
        prints = {id(a): _fingerprint(a["swatch"]) for a in apps}
        usable = [a for a in apps if prints[id(a)]]
        if len(usable) >= 3:
            columns = list(zip(*(prints[id(a)] for a in usable)))
            typical = [sorted(col)[len(col) // 2] for col in columns]
            rep = min(
                usable,
                key=lambda a: (
                    sum(abs(v - t) for v, t in zip(prints[id(a)], typical)),
                    a["catalogPage"],
                ),
            )

    if rep is None:
        rep = min(apps, key=lambda a: (colour_distance(a), a["catalogPage"]))

    spread = max(colour_distance(a) for a in apps) if len(apps) > 1 else 0
    metrics = color_metrics(tuple(med))
    metrics["appearanceCount"] = len(apps)
    metrics["spread"] = spread
    return rep, metrics


def aspect_outliers(colors) -> set[str]:
    """Swatch files whose proportions do not match the rest of their page.

    Rules and tint bands survive the text-overlap check — no type sits on them —
    but they are far longer and thinner than a bead strip. Comparing each crop
    against the median shape of its own page catches them without needing to
    know what a bead looks like.
    """
    by_page: dict[int, list[tuple[str, float]]] = {}
    for c in colors:
        for a in c["appearances"]:
            path = os.path.join(L.BUILD, "swatches", a["swatch"])
            if not os.path.exists(path):
                continue
            with Image.open(path) as im:
                w, h = im.size
            if h:
                by_page.setdefault(a["pdfPage"], []).append((a["swatch"], w / h))

    odd: set[str] = set()
    lo, hi = ASPECT_WINDOW
    for entries in by_page.values():
        ratios = sorted(r for _, r in entries)
        median = ratios[len(ratios) // 2]
        if median <= 0:
            continue
        for name, ratio in entries:
            rel = ratio / median
            if rel < lo or rel > hi:
                odd.add(name)
    return odd


def load_official() -> dict:
    """TOHO's own product index, keyed by catalogue colour number.

    The printed cells have to be cut out of outlined artwork, and a few per cent
    of those cuts land on a rule or a heading. The company photographs every
    colour for its own site, so where a colour appears there the photograph is
    simply a better picture of the bead than anything the PDF can yield.
    """
    if not os.path.exists(OFFICIAL_JSON):
        return {}
    with open(OFFICIAL_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def official_color(name: str) -> tuple[int, int, int] | None:
    """Representative colour of an official photo, ignoring its white ground."""
    path = os.path.join(OFFICIAL_IMG, name)
    if not os.path.exists(path):
        return None
    with Image.open(path) as im:
        small = im.convert("RGB").resize((48, 16), Image.BILINEAR)
    px = list(small.getdata())
    # The photos are beads on white; drop the ground before averaging.
    beads = [p for p in px if not (p[0] > 232 and p[1] > 232 and p[2] > 232)]
    if len(beads) < 12:
        beads = px
    beads.sort(key=sum)
    core = beads[len(beads) // 10 : max(len(beads) * 9 // 10, len(beads) // 10 + 1)]
    n = len(core)
    return tuple(sum(c[i] for c in core) // n for i in range(3))


def load(name: str):
    with open(os.path.join(L.BUILD, name), encoding="utf-8") as fh:
        return json.load(fh)


def build_catalog():
    colors = load("colors.json")
    finishes = load("finishes.json")

    misshapen = aspect_outliers(colors)
    official = load_official()

    line_index: dict[str, set] = {}
    for c in colors:
        for app in c["appearances"]:
            app["color"] = color_metrics(app["avgColor"])
            line_index.setdefault(app["line"], set()).update(app["beadTypes"])

    out_colors = []
    dropped = 0
    for c in colors:
        apps = sorted(c["appearances"], key=lambda a: (a["catalogPage"], a["printedAs"]))
        # A crop with type in it missed the artwork, so it must not be shown or
        # allowed to vote on the colour. Every colour keeps at least one.
        good = [
            a
            for a in apps
            if a["textOverlap"] <= MAX_TEXT_OVERLAP
            and not a["oversized"]
            and a["swatch"] not in misshapen
        ]
        dropped += len(apps) - len(good)
        # With no usable crop the entry is either a colour whose every cell was
        # contaminated or, more often, a heading bar that parsed as a number
        # ("着色ラスター" sits where a colour would). Either way the app must not
        # present the crop as the bead, so it is flagged rather than shown.
        unverified = not good
        if good:
            apps = good
        # Most colours are printed on several pages, so the appearances vote:
        # the colour is their per-channel median and the representative swatch is
        # whichever appearance sits closest to it. That is robust to the occasional
        # mis-cropped cell in a way that picking any single page is not.
        rep, consensus = consensus_color(apps)

        # Where TOHO publishes a photograph of the colour, that is the picture to
        # show and the colour to trust: it is the same product shot on a plain
        # ground, rather than a region cut out of printed artwork.
        site = official.get(c["key"])
        swatch = rep["swatch"]
        source = "catalog"
        if site:
            rgb = official_color(site["primary"])
            if rgb:
                consensus = {**color_metrics(rgb),
                             "appearanceCount": consensus["appearanceCount"],
                             "spread": consensus["spread"]}
                swatch = site["primary"]
                source = "official"
                unverified = False

        out_colors.append(
            {
                "key": c["key"],
                "number": c["number"],
                "suffix": c["suffix"],
                "matte": c["matte"],
                "unverified": unverified,
                "finishBase": c["finishBase"],
                "finishes": c["finishes"],
                "notes": suffix_notes(c["suffix"]),
                "color": consensus,
                "swatch": swatch,
                "swatchSource": source,
                "official": {
                    "printed": site["printed"],
                    "colorWords": site["colorWords"],
                    "finishes": site["finishes"],
                    "shapes": [
                        {"category": sh["category"], "size": sh["size"], "image": sh["local"]}
                        for sh in site["shapes"]
                    ],
                } if site else None,
                "lines": sorted({a["line"] for a in apps}),
                "beadTypes": sorted({t for a in apps for t in a["beadTypes"]}),
                "salesStyles": sorted({a["salesStyle"] for a in apps}),
                "appearances": [
                    {
                        "catalogPage": a["catalogPage"],
                        "line": a["line"],
                        "beadTypes": a["beadTypes"],
                        "salesStyle": a["salesStyle"],
                        "printedAs": a["printedAs"],
                        "printedForms": a["printedForms"],
                        "linePrefix": a["linePrefix"],
                        "swatch": a["swatch"],
                        "color": a["color"],
                        "variants": a["variants"],
                    }
                    for a in apps
                ],
            }
        )

    out_colors.sort(key=lambda c: (c["number"], c["suffix"]))
    return {
        "meta": {
            "title": "TOHO BEADS カタログ",
            "edition": EDITION,
            "source": "ビーズカタログ2021 第1部・第2部",
            "priceNote": PRICE_NOTE,
            "colorCount": len(out_colors),
            "appearanceCount": sum(len(c["appearances"]) for c in out_colors),
            "pageCount": len(CHART_PAGES) + len(NON_CHART_PAGES),
            "droppedAppearances": dropped,
        },
        "finishes": finishes["finishes"],
        "methods": [
            {"mark": "①", "name": "ラスター", "note": "ビーズの表面に、白色の照りを加えること。"},
            {"mark": "②", "name": "オーロラ", "note": "ビーズの表面に、レインボー光沢の照りを加えること。"},
            {"mark": "③", "name": "着色", "note": "ビーズに塗料及び染料で色を着けたもの。"},
            {"mark": "④", "name": "PF", "note": "従来の同色番に比べて摩擦に強く、色が落ちにくくなっています。"},
            {"mark": "⑤", "name": "蛍光", "note": "ネオンのように鮮やかに発色する色です。"},
            {"mark": "⑥", "name": "つや消し（F）", "note": "ビーズの表面をすりガラス状につや消し加工したもの。Fはfrostedの略字。"},
            {"mark": "⑦", "name": "L・A・B・C・D・H", "note": "色調を表す記号。5L(淡)←5A・5・5B・5C・5D・5H(濃)。"},
            {"mark": "⑧", "name": "FM", "note": "着色またはパールのつや消し加工で、つや消しが強いもの。"},
        ],
        "beadTypes": BEAD_TYPES,
        "salesStyles": SALES_STYLES,
        "lines": [
            {"name": name, "beadTypes": sorted(types)}
            for name, types in sorted(line_index.items())
        ],
        "colors": out_colors,
    }


def build_price_seed(raw_colors) -> dict:
    """Every product code the catalogue printed, with its printed price.

    Read from the unfiltered extraction rather than the catalogue: a cell can be
    dropped because its *crop* caught some type, which says nothing about the
    price and product code printed beside it. Discarding those too would lose
    codes the search box should still find.
    """
    entries: dict[str, dict] = {}
    for c in raw_colors:
        for app in c["appearances"]:
            for v in app["variants"]:
                code = v.get("productCode")
                if not code:
                    continue
                entries[code] = {
                    "colorKey": c["key"],
                    "line": app["line"],
                    "style": v.get("style") or app["salesStyle"],
                    "quantity": v.get("quantity"),
                    "price": v.get("price"),
                    "catalogPage": app["catalogPage"],
                }
    return {
        "meta": {
            "note": PRICE_NOTE,
            "currency": "JPY",
            "taxIncluded": False,
            "priceKind": "定価（本体価格）",
            "edition": EDITION,
            "codeCount": len(entries),
        },
        "prices": dict(sorted(entries.items())),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reseed", action="store_true",
                    help="data/prices.json を種データで上書きする（手編集を破棄）")
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    catalog = build_catalog()
    with open(os.path.join(DATA, "catalog.json"), "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, ensure_ascii=False, separators=(",", ":"))

    seed = build_price_seed(load("colors.json"))
    with open(os.path.join(DATA, "prices.seed.json"), "w", encoding="utf-8") as fh:
        json.dump(seed, fh, ensure_ascii=False, indent=1)

    live = os.path.join(DATA, "prices.json")
    if args.reseed or not os.path.exists(live):
        with open(live, "w", encoding="utf-8") as fh:
            json.dump(seed, fh, ensure_ascii=False, indent=1)
        print("wrote data/prices.json (%d codes)" % seed["meta"]["codeCount"])
    else:
        print("kept existing data/prices.json — 手編集は保持されます（--reseed で再生成）")

    # Only the swatches the catalogue actually references are served: the crops
    # dropped as low-quality stay in build/ for inspection but never ship.
    # Replaced rather than merged, so a changed cell set leaves no orphans.
    wanted = {a["swatch"] for c in catalog["colors"] for a in c["appearances"]}
    wanted |= {c["swatch"] for c in catalog["colors"] if c["swatchSource"] == "catalog"}
    shutil.rmtree(PUBLIC_SWATCHES, ignore_errors=True)
    os.makedirs(PUBLIC_SWATCHES, exist_ok=True)
    src = os.path.join(L.BUILD, "swatches")
    n = 0
    for name in sorted(wanted):
        shutil.copy2(os.path.join(src, name), os.path.join(PUBLIC_SWATCHES, name))
        n += 1

    # Official photographs are served alongside the catalogue crops.
    shutil.rmtree(PUBLIC_OFFICIAL, ignore_errors=True)
    n_official = 0
    if os.path.isdir(OFFICIAL_IMG):
        os.makedirs(PUBLIC_OFFICIAL, exist_ok=True)
        used = {c["swatch"] for c in catalog["colors"] if c["swatchSource"] == "official"}
        used |= {sh["image"] for c in catalog["colors"] if c["official"]
                 for sh in c["official"]["shapes"]}
        for name in sorted(used):
            src_path = os.path.join(OFFICIAL_IMG, name)
            if os.path.exists(src_path):
                shutil.copy2(src_path, os.path.join(PUBLIC_OFFICIAL, name))
                n_official += 1

    print("colours   : %d" % catalog["meta"]["colorCount"])
    print("公式写真  : %d色 / %d枚" % (
        sum(1 for c in catalog["colors"] if c["swatchSource"] == "official"), n_official))
    print("dropped   : %d low-quality appearances" % catalog["meta"]["droppedAppearances"])
    print("appearances: %d" % catalog["meta"]["appearanceCount"])
    print("swatches  : %d copied to public/swatches" % n)
    fams: dict[str, int] = {}
    for c in catalog["colors"]:
        fams[c["color"]["family"]] = fams.get(c["color"]["family"], 0) + 1
    print("hue families:", dict(sorted(fams.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
