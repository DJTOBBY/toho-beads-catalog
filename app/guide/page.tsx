import type { Metadata } from "next";
import Link from "next/link";
import { JsonLd } from "@/components/JsonLd";
import { getCatalog } from "@/lib/catalog";
import { BRAND, breadcrumbJsonLd, pageMetadata } from "@/lib/seo";

const GUIDE_TITLE = "ビーズの加工と形状";

export async function generateMetadata(): Promise<Metadata> {
  const catalog = await getCatalog();
  // Named from the data so the examples stay the ones the page actually shows.
  // Only the first few of each: the full lists run past what a snippet displays.
  const finishes = catalog.finishes.slice(0, 5).map((f) => f.name).join("・");
  const groups = [...new Set(catalog.beadTypes.map((t) => t.group))];

  return pageMetadata({
    path: "/guide/",
    title: `${GUIDE_TITLE}｜${BRAND}の仕上げ加工${catalog.finishes.length}種とサイズ一覧`,
    description:
      `${BRAND}の仕上げ加工${catalog.finishes.length}種類（${finishes}ほか）と、` +
      `${groups.slice(0, 2).join("・")}など形状${catalog.beadTypes.length}種のサイズ一覧。` +
      `丸小と丸大の違いや、カラーNo.末尾に付くL・D・Fなど記号の意味も解説します。`,
  });
}

export default async function GuidePage() {
  const catalog = await getCatalog();

  const groups: { group: string; types: typeof catalog.beadTypes }[] = [];
  for (const t of catalog.beadTypes) {
    const last = groups.at(-1);
    if (last?.group === t.group) last.types.push(t);
    else groups.push({ group: t.group, types: [t] });
  }

  return (
    <div className="pt-10">
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "色を探す", path: "/" },
          { name: GUIDE_TITLE, path: "/guide/" },
        ])}
      />
      <h1 className="text-[26px] font-semibold tracking-tight sm:text-[30px]">
        {GUIDE_TITLE}
      </h1>
      <p className="mt-2 max-w-2xl text-[14px] leading-relaxed" style={{ color: "var(--fg-2)" }}>
        カタログの「ビーズの加工の種類」「ビーズの形状 目次」に基づく一覧です。
        各加工に何色あるかは下の一覧で確認でき、実際の色は
        <Link href="/" style={{ color: "var(--accent)" }}>
          色を探すページ
        </Link>
        の「仕上げ加工」で絞り込めます。
      </p>

      <section className="mt-10">
        <h2 className="text-[16px] font-semibold tracking-tight">カラーNo.の読み方</h2>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {catalog.methods.map((m) => (
            <li
              key={m.mark}
              className="rounded-lg p-3"
              style={{ border: "1px solid var(--line)", background: "var(--bg-2)" }}
            >
              <p className="text-[13px] font-medium">
                <span className="mr-1.5" style={{ color: "var(--accent)" }}>
                  {m.mark}
                </span>
                {m.name}
              </p>
              <p className="mt-1 text-[12px] leading-relaxed" style={{ color: "var(--fg-2)" }}>
                {m.note}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-12">
        <h2 className="text-[16px] font-semibold tracking-tight">仕上げ加工の種類</h2>
        <div className="mt-3 grid gap-3">
          {catalog.finishes.map((f) => (
            <div
              key={f.name}
              className="rounded-lg p-4"
              style={{ border: "1px solid var(--line)", background: "var(--bg-2)" }}
            >
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h3 className="text-[14px] font-semibold">{f.name}</h3>
                <p className="text-[12px] leading-relaxed" style={{ color: "var(--fg-2)" }}>
                  {f.description}
                </p>
              </div>
              <ul className="mt-3 flex flex-wrap gap-1.5">
                {f.variations.map((v) => (
                  <li key={v.name}>
                    <span
                      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px]"
                      style={{ border: "1px solid var(--line)", color: "var(--fg-2)" }}
                    >
                      {v.name}
                      <span className="tabnum text-[10.5px]" style={{ color: "var(--fg-3)" }}>
                        {v.colorNumbers.length}色
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
              {f.variations.some((v) => v.note) && (
                <ul className="mt-2 grid gap-0.5 text-[11px]" style={{ color: "var(--fg-3)" }}>
                  {f.variations
                    .filter((v) => v.note)
                    .map((v) => (
                      <li key={v.name}>
                        {v.name}: ※{v.note}
                      </li>
                    ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-[16px] font-semibold tracking-tight">形状とサイズ</h2>
        <div className="mt-3 grid gap-6">
          {groups.map((g) => (
            <div key={g.group}>
              <h3 className="text-[13px] font-semibold" style={{ color: "var(--accent)" }}>
                {g.group}
              </h3>
              <div className="scroll-x mt-2">
                <table className="w-full min-w-[560px] border-collapse text-[13px]">
                  <tbody>
                    {g.types.map((t) => (
                      <tr key={t.key} style={{ borderTop: "1px solid var(--line)" }}>
                        <td className="w-[220px] py-2.5 pr-4 font-medium">{t.name}</td>
                        <td className="w-[150px] py-2.5 pr-4 tabnum" style={{ color: "var(--fg-2)" }}>
                          {t.size}
                        </td>
                        <td className="py-2.5 text-[12px]" style={{ color: "var(--fg-2)" }}>
                          {t.note}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-[16px] font-semibold tracking-tight">販売スタイル</h2>
        <ul className="mt-3 grid gap-3 sm:grid-cols-2">
          {catalog.salesStyles.map((s) => (
            <li
              key={s.key}
              className="rounded-lg p-4"
              style={{ border: "1px solid var(--line)", background: "var(--bg-2)" }}
            >
              <p className="text-[14px] font-semibold">{s.name}</p>
              <p className="mt-1 text-[12px] leading-relaxed" style={{ color: "var(--fg-2)" }}>
                {s.note}
              </p>
              <p className="mt-2 text-[11px] tabnum" style={{ color: "var(--fg-3)" }}>
                パッケージ: {s.pack}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-12">
        <h2 className="text-[16px] font-semibold tracking-tight">お取り扱い上の注意</h2>
        <ul className="mt-3 grid gap-2 text-[12.5px] leading-relaxed" style={{ color: "var(--fg-2)" }}>
          <li>
            銀メッキ・コゲ金・銅ラスター・仁丹メッキ・ニッケルメッキ・本金メッキ関係、No.702のカラーは、
            サラシ（漂白）による変色、あるいは長時間たつと酸化現象によって変色することがあります。
          </li>
          <li>
            コゲ金・銅ラスター・仁丹メッキ・ニッケルメッキ・本金メッキ・着色関係、No.702のカラーは、
            強い摩擦によって色落ちすることがあります。
          </li>
          <li>セイロン関係・着色関係は、太陽光線（紫外線）によって色落ち（退色）する場合があります。</li>
          <li>竹ビーズ・ツイストビーズ・シルクビーズは、強い衝撃によって割れる場合があります。</li>
          <li>
            ニッケルメッキ・No.712・712F・715・722は、金属アレルギーの方や肌に異常を感じた時は
            ご使用を中止いただき、専門医にご相談下さい。
          </li>
        </ul>
      </section>

      <p className="mt-12 text-[13px]">
        <Link href="/" style={{ color: "var(--accent)" }}>
          ← 色を探すページへ戻る
        </Link>
      </p>
    </div>
  );
}
