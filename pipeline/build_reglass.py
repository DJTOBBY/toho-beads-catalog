"""Fetch the RE:glass swatches and turn them into catalogue entries.

RE:glass is the one line that predates neither the 2021 catalogue nor the
company product index — it has its own site, so nothing upstream in this
pipeline knows about it. What it does share is the numbering: each RE:glass
colour is an existing catalogue number plus 5000, and it carries that number's
finish. That is what build_data.py uses to fold these 25 into the same filters
as the other 1,011 colours.

Run before build_data.py:

    python3 pipeline/build_reglass.py
"""

from __future__ import annotations

import io
import json
import os
import time
import urllib.request

from PIL import Image

import lib_pdf as L
import reglass_source as R

CACHE = os.path.join(L.BUILD, "reglass")
PUBLIC = os.path.join(L.REPO, "public", "reglass")
OUT = os.path.join(L.BUILD, "reglass.json")

# The site serves these as ~600px circles on white; the app never shows one
# larger than a card, so they are re-encoded down on the way in.
SERVE_WIDTH = 320
QUALITY = 86
PAUSE = 0.25


def fetch(item: dict) -> str:
    """Download one swatch into the cache, returning its path."""
    os.makedirs(CACHE, exist_ok=True)
    dst = os.path.join(CACHE, f"{item['key']}.{item['ext']}")
    if os.path.exists(dst):
        return dst
    req = urllib.request.Request(
        R.wix_url(item["media"], item["ext"]),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    with open(dst, "wb") as fh:
        fh.write(data)
    time.sleep(PAUSE)
    return dst


def encode(src: str, key: str) -> str:
    """Re-encode a cached swatch into public/reglass, returning its filename."""
    os.makedirs(PUBLIC, exist_ok=True)
    name = f"{key}.webp"
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > SERVE_WIDTH:
            h = round(im.height * SERVE_WIDTH / im.width)
            im = im.resize((SERVE_WIDTH, h), Image.LANCZOS)
        im.save(os.path.join(PUBLIC, name), "WEBP", quality=QUALITY, method=6)
    return name


def swatch_color(src: str) -> tuple[int, int, int]:
    """Representative colour of a swatch, ignoring the white ground.

    The site's swatches are a circle of beads on white, so unlike the strip
    photos there is a large corner area to discard. Sampling a centre crop
    avoids it without having to detect the circle.
    """
    with Image.open(src) as im:
        im = im.convert("RGB")
        s = min(im.width, im.height)
        # centre 60%: comfortably inside the circle at any of the sizes served.
        m = round(s * 0.2)
        im = im.crop((m, m, im.width - m, im.height - m)).resize((32, 32), Image.BILINEAR)
    px = list(im.getdata())
    beads = [p for p in px if not (p[0] > 236 and p[1] > 236 and p[2] > 236)]
    if len(beads) < 32:
        beads = px
    beads.sort(key=sum)
    core = beads[len(beads) // 10 : max(len(beads) * 9 // 10, len(beads) // 10 + 1)]
    n = len(core)
    return tuple(sum(c[i] for c in core) // n for i in range(3))


def main() -> None:
    entries = []
    for bottle, item in R.all_items():
        src = fetch(item)
        entries.append(
            {
                "key": item["key"],
                "base": item["base"],
                "matte": bool(item.get("matte")),
                "bottle": bottle["name"],
                "bottleEn": bottle["en"],
                "bottleSlug": bottle["slug"],
                "swatch": encode(src, item["key"]),
                "rgb": list(swatch_color(src)),
            }
        )
        print(f"{bottle['slug']:6} {item['key']:7} {entries[-1]['rgb']}")

    os.makedirs(L.BUILD, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"line": R.LINE, "sizes": R.SIZES, "colors": entries},
                  fh, ensure_ascii=False, indent=1)
    print(f"\n{len(entries)} 色 -> {OUT}")


if __name__ == "__main__":
    main()
