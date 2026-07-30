# TOHO BEADS カタログ Web アプリ

トーホービーズの「ビーズカタログ2021（第1部・第2部）」PDF から、一般消費者向けの
検索できるガラスビーズカタログを生成する Next.js アプリです。

- **色から探す** — カラーピッカーで色を選ぶと、OKLab 色空間での距離が近い順に並びます
- **絞り込み** — 色系統 / 仕上げ加工（20種・37バリエーション）/ ビーズ種別 / 販売スタイル / つや消し
- **検索** — カラーNo.・品番・加工名
- **カラー詳細** — そのカラーがどのビーズ・どの販売スタイルで展開されているか、価格と品番、
  同じ基本カラーNo.の濃淡（`5L → 5 → 5D`）、色の近いカラー

```bash
npm run dev
```

## 価格の更新

**価格は `data/prices.json` を直接編集してください。** 品番（6桁）がキーです。

```json
{
  "prices": {
    "800014": { "colorKey": "1", "line": "Aiko・トレジャービーズ", "style": "Aiko",
                "quantity": null, "price": 370, "catalogPage": 46 }
  }
}
```

- 掲載価格は **定価（本体価格・税抜）** です。卸価格ではありません。
- `npm run data`（パイプライン再実行）は `data/prices.json` を**上書きしません**。
  カタログ掲載時の値に戻したいときだけ `python3 pipeline/build_data.py --reseed` を使います。
- カタログ掲載時の値は `data/prices.seed.json` に常に保存されるので、差分の確認に使えます。
- 開発サーバーは価格ファイルをキャッシュしないため、保存すると再読み込みで即反映されます。

カタログ本体の価格表（カタログ P.70〜P.116）は元 PDF に含まれていないため、
価格が入っているのは誌面に直接価格が刷られていた品番のみです。それ以外のカラーは
アプリ上で「価格表をご参照ください」と表示されます。`prices.json` に品番を追記すれば
表示されるようになります。

## データパイプライン

元 PDF は Illustrator の印刷入稿データで、**全ページの文字がアウトライン化**されており
テキスト層がありません。そのため文字は OCR、図形は PDF 自身の構造から取り出します。

```bash
# 1. 全79ページを300dpiで描画し、macOS Vision でOCR（初回のみ・約3分）
swiftc -O pipeline/ocr_page.swift -o build/ocr_page
for i in $(seq 1 79); do
  n=$(printf "%02d" $i)
  python3 -c "import fitz;fitz.open('$TOHO_CATALOG_PDF')[$i-1].get_pixmap(dpi=300).save('build/pages_hi/p$n.png')"
  build/ocr_page build/pages_hi/p$n.png > build/ocr/p$n.json
done

# 2. 加工区分の対応表（カタログ P.6-7）を抽出
python3 pipeline/extract_finishes.py

# 3. カラーとスウォッチ画像を抽出（約3分）
python3 pipeline/extract_colors.py

# 4. アプリ用データを組み立て
python3 pipeline/build_data.py
```

PDF の場所は `TOHO_CATALOG_PDF` 環境変数で指定できます（既定は
`~/Downloads/ビーズカタログ2021-1-2部.pdf`）。

### 各ファイルの役割

| ファイル | 内容 |
| --- | --- |
| `pipeline/ocr_page.swift` | macOS Vision による OCR（文字＋座標を JSON 出力） |
| `pipeline/lib_pdf.py` | PDF 読み込み、OCR 結果の座標変換、罫線抽出 |
| `pipeline/lib_swatch.py` | カラーラベルの解析、スウォッチ領域の特定とトリミング、代表色算出 |
| `pipeline/page_map.py` | どのページがどの製品ライン・販売スタイルか（手作業で転記） |
| `pipeline/bead_types.py` | 形状とサイズの一覧（カタログ P.4-5 から転記） |
| `pipeline/extract_finishes.py` | 加工区分 → カラーNo. の公式対応表 |
| `pipeline/extract_colors.py` | カラー本体の抽出。`build/colors_report.json` に検証レポート |
| `pipeline/build_data.py` | `data/catalog.json` と価格レイヤーの生成 |
| `pipeline/verify_page.py` | 誌面と抽出結果を並べた検証シート（`build/verify/pNN.png`） |

### 抽出の設計上のポイント

- **カラーNo. の正当性は公式対応表で検証** します。誌面だけでは判別できない OCR の誤り
  （印刷された `81` が `8L` と読まれる等）が、実在するカラーNo. の一覧と突き合わせて解決します。
- **スウォッチは2D連結成分の最大ブロブ**として切り出します。●印・★印などの注記記号、
  セルの罫線、装飾図形が混入するのを防ぐためで、x軸への射影だけでは分離できません。
- **代表色は複数ページの多数決（中央値）** です。ほとんどのカラーは複数ページに掲載されており、
  誤クロップは外れ値として打ち消されます。
- **文字が写り込んだクロップは自動的に除外**します（`textOverlap`）。同様に、ページ内の
  標準的なセル寸法から大きく外れたクロップも除外します（`oversized`）。

### 既知の制約

- 元 PDF に価格表本体（カタログ P.70〜116）が含まれていません。
- カラーNo. のうち約 140 件は加工区分の対応表に載っていません。マガ玉（`M41xx`）や
  ミックス（`α-32xx`）のように独自採番のもの、糸通し専用色などが該当します。
  アプリ上では加工区分が空欄になります。
- 2021年版の誌面に4件のカンマ抜け誤植（`1203`+`1204` 等）があり、パイプラインが
  補正して `build/finishes.json` の `rejected` に記録しています。
- p68（シャーロット）/ p69（特小スリーカット）は1枚の写真に複数のサイズ行が付く
  レイアウトで、一部のセルが抽出できていません。除外済みなので誤った色は表示されませんが、
  掲載バリエーションの一覧は完全ではありません。

## 免責

ガラス特有の光沢や質感、微妙な色合いは写真・印刷・画面表示により実物とは異なります。
サイズ・粒数は目安です。
