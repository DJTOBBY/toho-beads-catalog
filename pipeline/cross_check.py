"""Compare the finishes read off the printed catalogue against TOHO's own data.

The catalogue's "ビーズの加工の種類" table (pages 6-7) was recovered by OCR, and
the site publishes the same classification per colour. Where the two disagree
one of them is wrong, and the disagreement is worth seeing rather than silently
preferring either — a systematic mismatch usually means a naming difference, a
handful of scattered ones usually means an OCR slip.

Output: build/cross_check.json and a summary on stdout.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_pdf as L

# The two sources name the same processes slightly differently. These pairs are
# the same finish, not a disagreement.
SYNONYMS = {
    "艶": {"ギョク"},          # the site spells 艶 as ギョク
    "つや消し": {"ツヤケシ"},
    "スキ": {"スキ"},
    "銀メッキ": {"銀メッキ"},
    "セイロン": {"セイロン"},
    "玉虫": {"玉虫"},
    "高級玉虫": {"高級玉虫"},
    "サニー": {"サニー"},
    "ブロンズ": {"ブロンズ"},
    "コゲ金": {"コゲ金"},
    "銅ラスター": {"銅ラスター"},
    "仁丹メッキ": {"仁丹メッキ"},
    "ニッケルメッキ": {"ニッケルメッキ"},
    "本金メッキ": {"本金メッキ"},
    "銅メッキ": {"銅メッキ"},
    "着色": {"着色"},
    "パール": {"パール"},
    "シルク": {"シルク"},
    "マーブル": {"マーブル"},
    "反射": {"反射"},
    "蓄光": {"蓄光"},
    "金彩": {"金彩"},
    "セミグレーズド": {"セミグレーズド"},
    "PF": {"ＰＦ", "PF"},
    "ラスター": {"ラスター"},
    "オーロラ": {"オーロラ"},
    "蛍光": {"蛍光"},
}


def normalise(name: str) -> set[str]:
    """The site-side tokens a catalogue finish name should map onto."""
    out: set[str] = set()
    for base, aliases in SYNONYMS.items():
        if base in name:
            out |= aliases
    return out


def satisfied(expected: set[str], theirs: set[str]) -> bool:
    """Whether the site lists every process the catalogue names.

    Matching is by substring because the two write the same thing at different
    lengths — the catalogue's "PF" is the site's "ＰＦ加工", its "オーロラ" their
    "オーロラ加工".
    """
    return all(any(want in have or have in want for have in theirs) for want in expected)


def main():
    catalog_path = os.path.join(L.REPO, "data", "catalog.json")
    official_path = os.path.join(L.BUILD, "web", "official.json")
    if not os.path.exists(official_path):
        raise SystemExit("run pipeline/fetch_official.py first")

    with open(catalog_path, encoding="utf-8") as fh:
        catalog = json.load(fh)
    with open(official_path, encoding="utf-8") as fh:
        official = json.load(fh)

    agree = disagree = only_catalog = only_site = 0
    rows = []
    unmapped = Counter()

    for c in catalog["colors"]:
        site = official.get(c["key"])
        # Only the variation is compared. The group name ("コゲ金・銅ラスター")
        # covers two processes and a colour has just one of them, so expanding it
        # would demand both and report a disagreement that is not there.
        mine = {v["variation"] for v in c["finishes"]}
        theirs = set(site["finishes"]) if site else set()

        if not site:
            only_catalog += 1
            continue
        if not c["finishes"]:
            only_site += 1
            rows.append({"key": c["key"], "kind": "誌面に加工区分なし",
                         "catalog": [], "site": sorted(theirs)})
            continue

        expected = set()
        for name in mine:
            expected |= normalise(name)
        if not expected:
            unmapped[tuple(sorted(mine))] += 1

        # The site lists every process applied; agreement means the catalogue's
        # names all appear there, not that the two lists are identical.
        if expected and satisfied(expected, theirs):
            agree += 1
        else:
            disagree += 1
            rows.append({"key": c["key"], "kind": "不一致",
                         "catalog": sorted(mine), "site": sorted(theirs),
                         "expected": sorted(expected)})

    report = {
        "agree": agree,
        "disagree": disagree,
        "onlyCatalog": only_catalog,
        "onlySite": only_site,
        "rows": rows[:400],
    }
    with open(os.path.join(L.BUILD, "cross_check.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    total = agree + disagree
    print("両方に加工区分がある色 : %d" % total)
    print("  一致              : %d (%.1f%%)" % (agree, 100 * agree / total if total else 0))
    print("  不一致            : %d" % disagree)
    print("公式にない色           : %d" % only_catalog)
    print("誌面に加工区分がない色   : %d" % only_site)
    if unmapped:
        print()
        print("対応表に無い誌面側の名称:")
        for names, n in unmapped.most_common(10):
            print("  %-40s %d色" % ("・".join(names), n))
    print()
    print("不一致の例:")
    for r in [r for r in rows if r["kind"] == "不一致"][:15]:
        print("  No.%-7s 誌面=%-22s 公式=%s" % (
            r["key"], "・".join(r["catalog"])[:22], "・".join(r["site"])))
    print()
    print("wrote build/cross_check.json")


if __name__ == "__main__":
    main()
