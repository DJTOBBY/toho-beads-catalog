"""Draw public/og.png, the card shown when a page of the site is shared.

next/og renders on request and this site has no server, so the share image has
to be a file. One file rather than 1,036: a card per colour would be better for
a shared link, but pre-rendering them would add a few hundred megabytes of
derived artwork to the repository for an image that is not read by search.

Run: python3 pipeline/og_image.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
OUT = PUBLIC / "og.png"

W, H = 1200, 630

PAPER = (250, 248, 245)
PAPER_2 = (242, 238, 232)
INK = (27, 26, 25)
INK_2 = (85, 80, 75)
INK_3 = (139, 131, 121)
ACCENT = (154, 91, 63)
LINE = (226, 219, 209)

FONT_DIR = Path("/System/Library/Fonts")
BOLD = FONT_DIR / "ヒラギノ角ゴシック W6.ttc"
REGULAR = FONT_DIR / "ヒラギノ角ゴシック W3.ttc"

# Where the site puts each kind of swatch, mirroring SWATCH_DIR in src/lib/color.ts.
SWATCH_DIR = {"official": "official", "catalog": "swatches", "reglass": "reglass"}

# The strip column on the right.
STRIP_X, STRIP_W, STRIP_H, STRIP_GAP = 640, 488, 84, 16
STRIP_COUNT = 5


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def photo_of(color: dict) -> Path:
    return PUBLIC / SWATCH_DIR[color["swatchSource"]] / color["swatch"]


def usable_photo(color: dict) -> Image.Image | None:
    """A photo only counts if it is a long strip shot on white.

    The catalogue crops are the same beads but framed every which way — some on
    black, some a circle of loose beads with the printed caption still in frame —
    and a column mixing those reads as a mistake rather than as a range.
    """
    try:
        im = Image.open(photo_of(color)).convert("RGB")
    except (OSError, KeyError):
        return None
    if im.width < im.height * 3.5:
        return None
    corner = im.crop((0, 0, 8, 8)).resize((1, 1)).getpixel((0, 0))
    if min(corner) < 215:
        return None
    return im


def sample_colors(colors: list[dict], n: int) -> list[Image.Image]:
    """A spread across the hue circle, so the card is not five browns."""
    usable = [c for c in colors if not c["unverified"] and c["swatchSource"] == "official"]

    picked: list[Image.Image] = []
    # Bands of equal hue width, not of equal population: the catalogue is a
    # quarter orange, so splitting by count would put three oranges in a row.
    for i in range(n):
        lo, hi = i * 360 / n, (i + 1) * 360 / n
        band = [c for c in usable if lo <= c["color"]["hue"] < hi] or usable
        # Saturated colours photograph as themselves; near-greys read as dirt at
        # this size, so each band gives up its most vivid member that has a
        # usable photo.
        for color in sorted(band, key=lambda c: -c["color"]["sat"]):
            im = usable_photo(color)
            if im is not None:
                picked.append(im)
                break
    return picked


def rounded(im: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius, fill=255)
    # Faded at the cut, the same way the size comparison on a colour page is, so
    # a strip reads as continuing past the frame rather than as ending there.
    fade_from = int(im.width * 0.82)
    for x in range(fade_from, im.width):
        t = (x - fade_from) / (im.width - fade_from)
        for y in range(im.height):
            mask.putpixel((x, y), int(mask.getpixel((x, y)) * (1 - t)))
    im.putalpha(mask)
    return im


def strip(photo: Image.Image) -> Image.Image:
    """One swatch photo, filled to the strip box from its left edge."""
    scale = STRIP_H / photo.height
    photo = photo.resize((max(1, round(photo.width * scale)), STRIP_H), Image.LANCZOS)

    box = Image.new("RGB", (STRIP_W, STRIP_H), (255, 255, 255))
    if photo.width < STRIP_W:
        # Short strips tile rather than stretch: a doubled bead still looks like
        # beads, a stretched one looks like a smear.
        for x in range(0, STRIP_W, photo.width):
            box.paste(photo, (x, 0))
    else:
        box.paste(photo, (0, 0))
    return rounded(box, 10)


def main() -> None:
    catalog = json.loads((ROOT / "data" / "catalog.json").read_text("utf-8"))
    count = catalog["meta"]["colorCount"]
    finishes = len(catalog["finishes"])

    card = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(card)

    # A paper-2 field behind the strips separates the photographs from the type
    # without drawing a box around them.
    draw.rectangle([STRIP_X - 56, 0, W, H], fill=PAPER_2)
    draw.line([(STRIP_X - 56, 0), (STRIP_X - 56, H)], fill=LINE, width=2)

    photos = sample_colors(catalog["colors"], STRIP_COUNT)
    total = len(photos) * STRIP_H + (len(photos) - 1) * STRIP_GAP
    top = (H - total) // 2
    for i, photo in enumerate(photos):
        tile = strip(photo)
        card.paste(tile, (STRIP_X, top + i * (STRIP_H + STRIP_GAP)), tile)

    x = 72
    draw.text((x, 96), "TOHO BEADS カタログ", font=font(BOLD, 30), fill=ACCENT)
    draw.text((x, 168), "トーホービーズの", font=font(BOLD, 58), fill=INK)
    draw.text((x, 240), "グラスビーズを、", font=font(BOLD, 58), fill=INK)
    draw.text((x, 312), "色から探す。", font=font(BOLD, 58), fill=ACCENT)

    draw.text(
        (x, 414),
        f"全{count:,}色 / 仕上げ加工{finishes}種",
        font=font(BOLD, 28),
        fill=INK_2,
    )
    draw.text(
        (x, 458),
        "カラーNo.・品番・加工・色から検索",
        font=font(REGULAR, 26),
        fill=INK_2,
    )
    draw.text(
        (x, 522),
        "djtobby.github.io/toho-beads-catalog",
        font=font(REGULAR, 22),
        fill=INK_3,
    )

    card.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
