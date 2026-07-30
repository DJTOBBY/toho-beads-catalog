"""Fetch TOHO's own product data and colour photographs.

The 2021 catalogue PDF is the source for what the printed edition says, but its
colour cells are outlined artwork that has to be cut out by inference, and a few
per cent of those cuts land on a rule or a heading instead of the beads. TOHO
publishes the same products at toho-beads.co.jp with one photograph per colour
and per shape, which is a far better picture than anything croppable from print.

This downloads:
  build/web/search_data.js     the site's own product index (already fetched)
  build/web/img/**             one photograph per colour number
  build/web/official.json      the index, normalised to the app's colour keys

Run:  python3 pipeline/fetch_official.py [--all]
      --all also fetches a photograph for every shape, not just one per colour.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_pdf as L
import lib_swatch as S

BASE = "http://www.toho-beads.co.jp"
DATA_URL = BASE + "/products/json/search_data.js"
WEB = os.path.join(L.BUILD, "web")
IMG_DIR = os.path.join(WEB, "img")

# Politeness: this is someone's small site, not a CDN.
PAUSE = 0.25
TIMEOUT = 30
UA = "TOHOBEADSBOOK-catalog-builder/1.0"

# Which shape to prefer when a colour is photographed several times. 丸小 is the
# catalogue's reference size and the one shoppers picture first.
SHAPE_PRIORITY = [
    "丸小ビーズ",
    "丸大ビーズ",
    "特小ビーズ",
    "ベストビーズ",
    "丸中ビーズ",
]


def fetch(url: str, path: str) -> bool:
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return True
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read()
    except (urllib.error.URLError, OSError):
        return False
    if not body:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(body)
    time.sleep(PAUSE)
    return True


def bracketed(value: str | None) -> list[str]:
    """The site stores multi-values as 「a」「b」."""
    return re.findall(r"「([^」]*)」", value or "")


def load_index() -> list[dict]:
    path = os.path.join(WEB, "search_data.js")
    if not os.path.exists(path):
        os.makedirs(WEB, exist_ok=True)
        if not fetch(DATA_URL, path):
            raise SystemExit("could not fetch %s" % DATA_URL)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["item"]


def normalise(items: list[dict]) -> dict[str, dict]:
    """Group the site's rows by the catalogue colour key the app uses."""
    out: dict[str, dict] = {}
    for it in items:
        printed = (it.get("c_n") or "").strip()
        label = S.parse_color_label(printed)
        if not label or not it.get("img"):
            continue
        rec = out.setdefault(
            label.key,
            {"key": label.key, "printed": printed, "shapes": [], "colorWords": set(), "finishes": set()},
        )
        rec["colorWords"].update(bracketed(it.get("c")))
        rec["finishes"].update(bracketed(it.get("fin")))
        rec["shapes"].append(
            {
                "category": (bracketed(it.get("cat")) or [""])[0],
                "title": it.get("ttl", ""),
                "size": (bracketed(it.get("size")) or [""])[0],
                "img": it["img"],
                "note": it.get("rmk", ""),
            }
        )
    for rec in out.values():
        rec["colorWords"] = sorted(rec["colorWords"])
        rec["finishes"] = sorted(rec["finishes"])
    return out


def pick_shape(rec: dict) -> dict:
    def rank(shape: dict) -> tuple[int, str]:
        cat = shape["category"]
        for i, want in enumerate(SHAPE_PRIORITY):
            if cat == want:
                return i, cat
        return len(SHAPE_PRIORITY), cat

    return min(rec["shapes"], key=rank)


def local_name(img_path: str) -> str:
    return img_path.lstrip("/").replace("/", "_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="全形状の写真を取得する")
    args = ap.parse_args()

    items = load_index()
    index = normalise(items)
    print("公式データ: %d件 / 色番 %d色" % (len(items), len(index)))

    wanted: list[tuple[str, str]] = []
    for rec in index.values():
        shapes = rec["shapes"] if args.all else [pick_shape(rec)]
        for shape in shapes:
            wanted.append((BASE + shape["img"], os.path.join(IMG_DIR, local_name(shape["img"]))))

    seen = set()
    unique = [(u, p) for u, p in wanted if not (p in seen or seen.add(p))]
    print("取得対象: %d枚" % len(unique))

    ok = failed = 0
    for i, (url, path) in enumerate(unique, 1):
        if fetch(url, path):
            ok += 1
        else:
            failed += 1
        if i % 100 == 0:
            print("  %d/%d  成功 %d / 失敗 %d" % (i, len(unique), ok, failed))

    for rec in index.values():
        for shape in rec["shapes"]:
            shape["local"] = local_name(shape["img"])
        rec["primary"] = local_name(pick_shape(rec)["img"])

    with open(os.path.join(WEB, "official.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)

    print("完了: 成功 %d / 失敗 %d" % (ok, failed))
    print("wrote build/web/official.json")


if __name__ == "__main__":
    main()
