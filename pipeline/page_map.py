"""Which catalogue page shows which bead line, and in which sales style.

Curated by hand. The page headings are set in an outlined display face that OCR
reads unreliably (丸小 comes back as "対ポ", 特大 as "特犬"), so the mapping is
transcribed from the catalogue's own "ビーズの形状 目次" index on catalogue pages
4-5 and checked against each rendered page.

Keys are 1-based PDF page numbers; catalogue page = PDF page - 7.

`layout` picks the swatch anchor:
  "strip" – colour number at the left of the cell, bead strip to its right
  "photo" – a round or square product photo with its label underneath
`style` is the sales style the page belongs to, matching taxonomy.json.
"""

# fmt: off
CHART_PAGES: dict[int, dict] = {
    15: dict(line="丸小・丸大ビーズ",        types=["丸小", "丸大"],       style="バラパック", layout="strip"),
    16: dict(line="丸小・丸大ビーズ（つや消し）", types=["丸小", "丸大"],   style="バラパック", layout="strip"),
    17: dict(line="丸小・丸大ビーズ",        types=["丸小", "丸大"],       style="バラパック", layout="strip"),
    18: dict(line="丸小・丸大ビーズ（つや消し）", types=["丸小", "丸大"],   style="バラパック", layout="strip"),
    19: dict(line="ロイヤルビーズ 丸小",      types=["丸小"],              style="バラパック", layout="strip"),
    20: dict(line="セラビーズ",              types=["丸小"],              style="バラパック", layout="photo"),
    21: dict(line="セラビーズ",              types=["丸小"],              style="バラパック", layout="photo"),
    22: dict(line="セラビーズ",              types=["丸小"],              style="バラパック", layout="photo"),
    23: dict(line="PFビーズ",               types=["丸小"],              style="バラパック", layout="photo"),
    24: dict(line="マーブルビーズ",           types=["丸小"],              style="バラパック", layout="photo"),
    25: dict(line="ピカットビーズ",           types=["丸小"],              style="バラパック", layout="photo"),
    26: dict(line="YUMI SHINE 蓄光ビーズ",   types=["丸小"],              style="バラパック", layout="photo"),
    27: dict(line="Takumi LHビーズ",         types=["Takumi LH丸小", "Takumi LH丸中"], style="バラパック", layout="strip"),
    28: dict(line="Takumi LHビーズ",         types=["Takumi LH丸小", "Takumi LH丸中"], style="バラパック", layout="strip"),
    29: dict(line="特大ビーズ",              types=["特大4mm", "特大5.5mm"], style="バラパック", layout="strip"),
    30: dict(line="シルクビーズ",             types=["竹ビーズ"],           style="バラパック", layout="strip"),
    31: dict(line="マガ玉ビーズ",             types=["マガ玉3mm", "マガ玉4mm"], style="バラパック", layout="strip"),
    32: dict(line="マガ玉ビーズ",             types=["マガ玉5mm", "マガ玉7mm"], style="バラパック", layout="photo"),
    33: dict(line="三角ビーズ",              types=["三角5mm", "三角7mm"], style="バラパック", layout="strip"),
    34: dict(line="三角ビーズ",              types=["三角中"],             style="バラパック", layout="strip"),
    35: dict(line="竹ビーズ・ツイストビーズ",    types=["一分竹", "二分竹", "ツイストビーズ"], style="バラパック", layout="strip"),
    36: dict(line="ロイヤルビーズ 竹",         types=["一分竹", "二分竹"],   style="バラパック", layout="strip"),
    37: dict(line="六角特小ビーズ",           types=["六角特小"],           style="バラパック", layout="strip"),
    38: dict(line="四角ビーズ",              types=["四角3mm", "四角4mm"], style="バラパック", layout="strip"),
    39: dict(line="特小ビーズ",              types=["特小"],              style="バラパック", layout="strip"),
    40: dict(line="特小ビーズ",              types=["特小"],              style="バラパック", layout="strip"),
    41: dict(line="グラスビーズミックス",       types=["ミックスビーズ"],      style="バラパック", layout="photo"),
    42: dict(line="ミックスビーズ",           types=["ミックスビーズ"],      style="バラパック", layout="strip"),
    45: dict(line="DEMIビーズ",             types=["DEMI丸小", "DEMI丸大", "DEMI特大"], style="バラパック", layout="strip"),
    46: dict(line="DEMIビーズ",             types=["DEMI丸小", "DEMI丸大", "DEMI特大"], style="バラパック", layout="strip"),
    47: dict(line="クィーンビーズ",           types=["丸小", "丸大", "特大4mm"], style="クィーン",  layout="strip"),
    48: dict(line="クィーンビーズ",           types=["特大5.5mm", "マガ玉4mm", "ミックスビーズ"], style="クィーン", layout="strip"),
    49: dict(line="クィーンビーズ 36色",      types=["丸小"],              style="クィーン",  layout="strip"),
    50: dict(line="クィーンビーズ 36色",      types=["特小"],              style="クィーン",  layout="strip"),
    53: dict(line="Aiko・トレジャービーズ",    types=["Aiko丸小", "トレジャー丸小"], style="Aiko・クィーン", layout="strip"),
    54: dict(line="Aiko・トレジャービーズ",    types=["Aiko丸小", "トレジャー丸小"], style="Aiko・クィーン", layout="strip"),
    55: dict(line="Aiko・トレジャービーズ",    types=["Aiko丸小", "トレジャー丸小"], style="Aiko・クィーン", layout="strip"),
    56: dict(line="Aiko・トレジャービーズ",    types=["Aiko丸小", "トレジャー丸小"], style="Aiko・クィーン", layout="strip"),
    57: dict(line="丸小・丸大ビーズ",         types=["丸小", "丸大"],       style="糸通し",    layout="strip"),
    58: dict(line="丸小・丸大ビーズ",         types=["丸小", "丸大", "丸中"], style="糸通し",   layout="strip"),
    59: dict(line="丸小ビーズ",              types=["丸小", "丸中"],       style="糸通し",    layout="strip"),
    60: dict(line="竹ビーズ・シルクビーズ",     types=["五厘竹", "一分竹", "二分竹", "三分竹"], style="糸通し", layout="strip"),
    61: dict(line="六角ビーズ・特大ビーズ",     types=["六角小", "六角大", "特大4mm"], style="糸通し", layout="strip"),
    62: dict(line="六角ビーズ",              types=["六角小", "六角大"],    style="糸通し",    layout="strip"),
    63: dict(line="マガ玉ビーズ・三角ビーズ",   types=["マガ玉4mm", "三角中"], style="糸通し",   layout="strip"),
    64: dict(line="三角ビーズ",              types=["三角小", "三角中", "三角大"], style="糸通し", layout="strip"),
    65: dict(line="六角特小ビーズ・スリーカット", types=["六角特小", "スリーカット特小"], style="糸通し", layout="strip"),
    66: dict(line="スリーカット・ダブルスリーカット", types=["スリーカット丸小", "スリーカット丸大"], style="糸通し", layout="strip"),
    68: dict(line="シャーロットビーズ",        types=["シャーロット特小", "シャーロット丸小"], style="糸通し", layout="strip"),
    69: dict(line="特小スリーカットビーズ",     types=["スリーカット特小"],    style="糸通し",    layout="strip"),
    71: dict(line="特小ビーズ",              types=["特小"],              style="糸通し",    layout="strip"),
    72: dict(line="特小ビーズ",              types=["特小"],              style="糸通し",    layout="strip"),
    73: dict(line="UNISEX PARTS",           types=["パーツ"],             style="バラパック", layout="photo"),
    74: dict(line="ヴィーダ・mimi（無穴ビーズ）", types=["ヴィーダ", "mimi特小"], style="バラパック", layout="photo"),
}
# fmt: on

# Pages that carry photography, explanations or price indexes rather than a
# colour chart. Recorded so the pipeline can assert it has seen all 79 pages.
NON_CHART_PAGES = {
    **{p: "表紙・イメージ写真" for p in range(1, 9)},
    9: "CONTENTS",
    10: "カタログご利用に際して",
    11: "ビーズの形状 目次",
    12: "ビーズの形状 目次",
    13: "ビーズの加工の種類",
    14: "ビーズの加工の種類・加工方法の説明",
    43: "DEMIビーズ 扉",
    44: "DEMIビーズ 作品例",
    51: "Aiko・トレジャービーズ 扉",
    52: "Aikoとは・Treasureとは",
    67: "アンバーカラービーズ スリーカット",
    70: "ワンダーカラービーズ",
    75: "参考 グラスビーズ粒数表",
    76: "参考 糸通しビーズ粒数表",
    77: "価格表 目次",
    78: "TOHOBEADS ENTERTAINMENT",
    79: "裏表紙",
}
