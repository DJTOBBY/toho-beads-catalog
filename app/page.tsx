import type { Metadata } from "next";

import { CatalogBrowser } from "@/components/CatalogBrowser";
import { JsonLd } from "@/components/JsonLd";
import { getCatalog, getPrices, toIndex } from "@/lib/catalog";
import { BRAND, pageMetadata, websiteJsonLd } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const catalog = await getCatalog();
  return pageMetadata({
    path: "/",
    title: `${BRAND} カラーカタログ｜全${catalog.meta.colorCount}色をカラーNo.・品番・色から探す`,
    description:
      `${BRAND}のグラスビーズ${catalog.meta.colorCount}色のカラーチャート。` +
      `カラーNo.・品番・仕上げ加工${catalog.finishes.length}種・ビーズ種別・色の呼び名で絞り込め、` +
      `選んだ色に近い順にも並べ替えられます。丸小・丸大・特小のサイズ比較と価格・品番つき。`,
  });
}

export default async function HomePage() {
  const [catalog, prices] = await Promise.all([getCatalog(), getPrices()]);

  const finishGroups = catalog.finishes.map((f) => ({
    finish: f.name,
    variations: f.variations.map((v) => v.name),
  }));

  const beadGroups: { group: string; types: { key: string; name: string }[] }[] = [];
  for (const t of catalog.beadTypes) {
    const last = beadGroups.at(-1);
    if (last?.group === t.group) last.types.push({ key: t.key, name: t.name });
    else beadGroups.push({ group: t.group, types: [{ key: t.key, name: t.name }] });
  }

  // One searchable string of product codes per colour, so typing a 品番 finds it.
  const codeIndex: Record<string, string> = {};
  for (const [code, entry] of Object.entries(prices.prices)) {
    codeIndex[entry.colorKey] = (codeIndex[entry.colorKey] ?? "") + code + " ";
  }

  const withPrice = new Set(Object.values(prices.prices).map((p) => p.colorKey));

  // TOHO's own colour words, ordered by how many colours carry each.
  const wordCounts = new Map<string, number>();
  for (const c of catalog.colors) {
    for (const w of c.official?.colorWords ?? []) {
      wordCounts.set(w, (wordCounts.get(w) ?? 0) + 1);
    }
  }
  const colorWords = [...wordCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([w]) => w);

  return (
    <>
      <JsonLd data={websiteJsonLd(catalog.meta.colorCount)} />
      <section className="pt-10 sm:pt-14">
        <h1 className="max-w-3xl text-[26px] font-semibold leading-tight tracking-tight sm:text-[34px]">
          トーホービーズの
          <wbr />
          グラスビーズを、
          <span style={{ color: "var(--accent)" }}>色から</span>
          探す。
        </h1>
        <p
          className="mt-3 max-w-2xl text-[14px] leading-relaxed sm:text-[15px]"
          style={{ color: "var(--fg-2)" }}
        >
          <strong className="tabnum font-semibold" style={{ color: "var(--fg)" }}>
            {catalog.meta.colorCount}
          </strong>
          色を、カラーNo.・品番・仕上げ加工・ビーズ種別で絞り込めます。
          色見本をタップすると、その色がどのビーズで作られているかがわかります。
        </p>
        <dl className="mt-6 flex flex-wrap gap-x-8 gap-y-3 text-[12px]">
          <Stat label="収録カラー" value={`${catalog.meta.colorCount} 色`} />
          {catalog.meta.reglass && (
            <Stat label="RE:glass" value={`${catalog.meta.reglass.count} 色`} />
          )}
          <Stat label="掲載バリエーション" value={`${catalog.meta.appearanceCount} 件`} />
          <Stat label="仕上げ加工" value={`${catalog.finishes.length} 種類`} />
          <Stat label="価格収録" value={`${withPrice.size} 色 / ${prices.meta.codeCount} 品番`} />
          <Stat label="版" value={catalog.meta.edition} />
        </dl>
      </section>

      <CatalogBrowser
        colors={toIndex(catalog.colors)}
        finishGroups={finishGroups}
        beadGroups={beadGroups}
        salesStyles={[...new Set(catalog.colors.flatMap((c) => c.salesStyles))].sort()}
        colorWords={colorWords}
        codeIndex={codeIndex}
        reglass={
          catalog.meta.reglass
            ? { name: catalog.meta.reglass.name, count: catalog.meta.reglass.count }
            : null
        }
      />
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt style={{ color: "var(--fg-3)" }}>{label}</dt>
      <dd className="tabnum mt-0.5 text-[14px] font-medium">{value}</dd>
    </div>
  );
}
