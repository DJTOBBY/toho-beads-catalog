"""Compare the printed 丸小・丸大 SAMPLE CARD against the catalogue data.

The card is what TOHO actually stocks in round beads, so it is the sharpest test
of coverage available: anything printed there and missing here is a real gap,
and anything here but not there is either a discontinued colour the 2021
catalogue still listed, or a number that was misread out of the PDF.

Output: build/sample_card_check.json and a summary on stdout.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_pdf as L
import lib_swatch as S
from sample_card import numbers


def main():
    with open(os.path.join(L.REPO, "data", "catalog.json"), encoding="utf-8") as fh:
        catalog = json.load(fh)

    official_path = os.path.join(L.BUILD, "web", "official.json")
    official = {}
    if os.path.exists(official_path):
        with open(official_path, encoding="utf-8") as fh:
            official = json.load(fh)

    # Both sides go through the same label parser so "45A" and "2151S" compare
    # the way the app keys them.
    card: dict[str, str] = {}
    unparsed = []
    for printed in numbers():
        label = S.parse_color_label(printed)
        if label:
            card.setdefault(label.key, printed)
        else:
            unparsed.append(printed)

    mine = {c["key"]: c for c in catalog["colors"]}
    # The round-bead colours the app knows about, by any route.
    round_keys = {
        c["key"]
        for c in catalog["colors"]
        if any(t in ("丸小", "丸大", "丸中") for t in c["beadTypes"])
        or any(
            sh["category"] in ("丸小ビーズ", "丸大ビーズ", "丸中ビーズ")
            for sh in (c["official"] or {}).get("shapes", [])
        )
    }

    missing = {k: p for k, p in card.items() if k not in mine}
    present_wrong_type = {
        k: p for k, p in card.items() if k in mine and k not in round_keys
    }
    extra = sorted(round_keys - set(card))

    report = {
        "cardCount": len(card),
        "unparsed": unparsed,
        "missingFromApp": missing,
        "notMarkedRound": present_wrong_type,
        "inAppNotOnCard": extra,
    }
    with open(os.path.join(L.BUILD, "sample_card_check.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    print("見本帳の色数         : %d" % len(card))
    print("  アプリに無い       : %d" % len(missing))
    print("  あるが丸小・丸大扱いでない: %d" % len(present_wrong_type))
    print("アプリの丸小・丸大    : %d" % len(round_keys))
    print("  見本帳に無い       : %d" % len(extra))
    if unparsed:
        print("解析できない表記     :", unparsed)
    print()
    if missing:
        print("■ 見本帳にあってアプリに無い色:")
        for k, p in sorted(missing.items(), key=lambda kv: (len(kv[0]), kv[0])):
            has_photo = "公式写真あり" if k in official else "公式写真なし"
            print("   %-8s (誌面表記 %-8s) %s" % (k, p, has_photo))
    print()
    print("wrote build/sample_card_check.json")


if __name__ == "__main__":
    main()
