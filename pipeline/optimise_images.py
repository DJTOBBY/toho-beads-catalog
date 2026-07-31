"""Re-encode the served images as WebP.

The photographs come off the site as JPEG at roughly 30 KB each; at ~3,300 of
them that is over 100 MB in the repository and over the wire. WebP at a high
quality setting halves that without a visible difference on swatches this size,
and every browser the app supports reads it.

Run after build_data.py. Rewrites public/official in place and updates the
image names in data/catalog.json to match.
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_pdf as L

PUBLIC_OFFICIAL = os.path.join(L.REPO, "public", "official")
CATALOG = os.path.join(L.REPO, "data", "catalog.json")
QUALITY = 86

# The catalogue photographs are small; anything wider than this is being scaled
# down in the browser anyway.
MAX_WIDTH = 560


def main():
    with open(CATALOG, encoding="utf-8") as fh:
        catalog = json.load(fh)

    # macOS occasionally leaves "name 2.jpg" copies behind in a synced folder;
    # they are never referenced and only inflate the checkout.
    referenced: set[str] = set()
    for c in catalog["colors"]:
        if c["swatchSource"] == "official":
            referenced.add(c["swatch"])
        for sh in (c["official"] or {}).get("shapes", []):
            referenced.add(sh["image"])

    removed = 0
    for name in os.listdir(PUBLIC_OFFICIAL):
        if name not in referenced:
            os.remove(os.path.join(PUBLIC_OFFICIAL, name))
            removed += 1

    before = after = 0
    renames: dict[str, str] = {}
    for name in sorted(referenced):
        src = os.path.join(PUBLIC_OFFICIAL, name)
        if not os.path.exists(src):
            continue
        stem = os.path.splitext(name)[0]
        out_name = stem + ".webp"
        dst = os.path.join(PUBLIC_OFFICIAL, out_name)

        before += os.path.getsize(src)
        with Image.open(src) as im:
            im = im.convert("RGB")
            if im.width > MAX_WIDTH:
                im.thumbnail((MAX_WIDTH, MAX_WIDTH * 4))
            im.save(dst, "WEBP", quality=QUALITY, method=5)
        after += os.path.getsize(dst)
        if dst != src:
            os.remove(src)
        renames[name] = out_name

    for c in catalog["colors"]:
        if c["swatchSource"] == "official":
            c["swatch"] = renames.get(c["swatch"], c["swatch"])
        for sh in (c["official"] or {}).get("shapes", []):
            sh["image"] = renames.get(sh["image"], sh["image"])

    with open(CATALOG, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, ensure_ascii=False, separators=(",", ":"))

    print("未参照ファイルを削除: %d枚" % removed)
    print("変換: %d枚  %.1f MB → %.1f MB (%.0f%%減)" % (
        len(renames), before / 1e6, after / 1e6,
        100 * (1 - after / before) if before else 0))


if __name__ == "__main__":
    main()
