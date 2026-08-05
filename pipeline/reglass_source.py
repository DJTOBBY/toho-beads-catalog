"""RE:glass beads — the one product line that is not in the 2021 catalogue.

TOHO makes these from recycled bottle cullet, so the colour comes from the
bottle rather than from a dye. The line lives on its own site
(tohobeads.info/<bottle>) instead of in the printed catalogue, which is why it
has to be described by hand here rather than extracted from the PDF.

The colour numbers turn out to be the catalogue's own numbers plus 5000: 5001
is 1 (スキ), 5101 is 101 (スキラスター), PF5021 is 21 (銀メッキ/PF). That mapping
is what lets these colours join the same finish and colour-word filters as
everything else — see build_reglass.py.
"""

# Bottle colour -> the catalogue number each RE:glass variation mirrors.
# Order matches the order the five swatches appear on each bottle's page.
BOTTLES = [
    {
        "slug": "clear",
        "name": "クリア",
        "en": "Clear Bottle",
        "items": [
            {"key": "5001", "base": "1", "media": "0628a9_a1bdad36de3045088971e1b7138965d7~mv2", "ext": "png"},
            {"key": "5001F", "base": "1", "matte": True, "media": "0628a9_4ba140a36e6d4744a553397595016801~mv2", "ext": "png"},
            {"key": "PF5021", "base": "21", "media": "0628a9_0642ff6acf0543f9a1a332b71d345358~mv2", "ext": "png"},
            {"key": "5101", "base": "101", "media": "0628a9_be4601c77a9b420ca777d4369b9c1126~mv2", "ext": "png"},
            {"key": "5161", "base": "161", "media": "0628a9_6bb5b2c282fe4c8f855f6146edb97248~mv2", "ext": "png"},
        ],
    },
    {
        "slug": "brown",
        "name": "ブラウン",
        "en": "Brown Bottle",
        "items": [
            {"key": "5002", "base": "2", "media": "0628a9_999a56894e8042f4ab7f6ac9281462db~mv2", "ext": "png"},
            {"key": "5002F", "base": "2", "matte": True, "media": "0628a9_9f1f2088e3da44d39486698adfda8b5e~mv2", "ext": "png"},
            {"key": "PF5022", "base": "22", "media": "0628a9_c305870b6d4946cea65d9e3961365511~mv2", "ext": "png"},
            {"key": "5103", "base": "103", "media": "0628a9_2509c81e759549579736870ab94f80a1~mv2", "ext": "png"},
            {"key": "5162", "base": "162", "media": "0628a9_23b0a75910904a319d6ab25c0fd2b3c4~mv2", "ext": "png"},
        ],
    },
    {
        "slug": "green",
        "name": "グリーン",
        "en": "Green Bottle",
        "items": [
            {"key": "5004", "base": "4", "media": "0628a9_6b4c8939353c4d19b5746267bb96b408~mv2", "ext": "jpg"},
            {"key": "5004F", "base": "4", "matte": True, "media": "0628a9_6e9f8abdf6e24843b696057aba34b05b~mv2", "ext": "jpg"},
            {"key": "PF5024", "base": "24", "media": "0628a9_e9c188b949184cafbc1edbe71db6cf72~mv2", "ext": "png"},
            {"key": "5105", "base": "105", "media": "0628a9_fcac2c3787ef4abfa9e802ec3fa496fc~mv2", "ext": "png"},
            {"key": "5164", "base": "164", "media": "0628a9_ed8e1ac5e32e40f4b6a6f8dd8074fd66~mv2", "ext": "jpg"},
        ],
    },
    {
        "slug": "blue",
        "name": "ブルー",
        "en": "Blue Bottle",
        "items": [
            {"key": "5013", "base": "13", "media": "0628a9_c3adf8a572c8499eb0199c310aa5a7b4~mv2", "ext": "png"},
            {"key": "5013F", "base": "13", "matte": True, "media": "0628a9_26b2991ed38242058f385db84603d70b~mv2", "ext": "png"},
            {"key": "PF5033", "base": "33", "media": "0628a9_c86592bd3f8f4016b338df310c778699~mv2", "ext": "png"},
            {"key": "5107", "base": "107", "media": "0628a9_d9d7f4a8054241fa996b243a3782f13e~mv2", "ext": "png"},
            {"key": "5168", "base": "168", "media": "0628a9_bcf76b3c26c34a359051c8b9c75eccb9~mv2", "ext": "png"},
        ],
    },
    {
        "slug": "black",
        "name": "ブラック",
        "en": "Black Bottle",
        "items": [
            {"key": "5009", "base": "9", "media": "0628a9_2c4015c6c8a14b4da82482b7a252eca1~mv2", "ext": "png"},
            {"key": "5009F", "base": "9", "matte": True, "media": "0628a9_ae11d2044fad4b139f58f2baaaabe359~mv2", "ext": "png"},
            {"key": "PF5029", "base": "29", "media": "0628a9_2c78c826dc7d4c51b2d7b5ef159e7e44~mv2", "ext": "png"},
            {"key": "5113", "base": "113", "media": "0628a9_c1ac42c5a24a4ccb829b706bc5aeda78~mv2", "ext": "png"},
            {"key": "5176", "base": "176", "media": "0628a9_d4f3e844c1ec4f45b3d753e05b5a5b5e~mv2", "ext": "png"},
        ],
    },
]

# The line is only made in these two, unlike the catalogue colours which run
# across a dozen shapes.
SIZES = [
    {"category": "丸小ビーズ", "size": "2.2", "mm": 2.2},
    {"category": "丸大ビーズ", "size": "3.0", "mm": 3.0},
]

LINE = {
    "id": "reglass",
    "name": "RE:glass beads",
    "nameJa": "リグラスビーズ",
    "note": "回収したガラス瓶を再生したビーズ。着色せず瓶そのものの色を活かすため、ロットごとに色差が出ます。",
    "site": "https://tohobeads.net/reglassbeads/",
}


def wix_url(media: str, ext: str, width: int = 600) -> str:
    """Full-bleed render of a Wix media item at a known width."""
    return f"https://static.wixstatic.com/media/{media}.{ext}/v1/fill/w_{width},h_{width},al_c,q_90/{media}.{ext}"


def all_items():
    for bottle in BOTTLES:
        for item in bottle["items"]:
            yield bottle, item
