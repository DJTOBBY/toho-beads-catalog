import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  type BeadColor,
  type Catalog,
  findColor,
  getCatalog,
  getPrices,
  toneSiblings,
} from "@/lib/catalog";
import { contrastInk, hexToOklab, oklabDistance, swatchUrl } from "@/lib/color";

type Params = { params: Promise<{ key: string }> };

// Pixels per millimetre of bead. The photos are not all shot at one
// magnification — a スリーカット特小 at 1.6 mm comes back taller than a 丸小 at
// 2.1 mm — so the drawn height is computed from the real size rather than taken
// from the file, which is what makes 丸小 and 丸大 differ by their true ratio.
const PX_PER_MM = 28;

// Beads sized by length rather than diameter: their photo shows the tube lying
// down, so its height is the tube's width and the size label says nothing about
// it. These keep the photo's own proportions.
const LENGTHWISE = ["竹ビーズ", "ツイスト", "スパイラル"];
const LENGTHWISE_SCALE = 0.75;

// Some photos are framed wider than others, so drawing them at true scale would
// mean enlarging a small file — 特大 4mm arrives only 64 px tall — and a blurred
// bead reads worse than one drawn a little under size. Past this the photo keeps
// its own resolution; the order of sizes still holds.
const MAX_UPSCALE = 1.25;

// How much of each strip is shown. Every window is the same width so the eye
// compares bead size, not strip length.
const SHAPE_WINDOW = 190;

// Softens the cut edge so a cropped strip reads as continuing past the frame.
const SHAPE_FADE = "linear-gradient(to right, #000 0 74%, transparent 100%)";

export async function generateStaticParams() {
  const catalog = await getCatalog();
  return catalog.colors.map((c) => ({ key: c.key }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { key } = await params;
  const catalog = await getCatalog();
  const color = findColor(catalog, decodeURIComponent(key));
  if (!color) return { title: "見つかりませんでした | TOHO BEADS カタログ" };
  const finish = color.finishes[0]?.variation ?? "";
  return {
    title: `カラーNo.${color.key}${finish ? `（${finish}）` : ""} | TOHO BEADS カタログ`,
    description: `トーホービーズ カラーNo.${color.key}。${
      finish ? `仕上げ加工は${finish}。` : ""
    }${color.beadTypes.slice(0, 6).join("・")}などで展開しています。`,
  };
}

export default async function ColorPage({ params }: Params) {
  const { key } = await params;
  const decoded = decodeURIComponent(key);
  const [catalog, prices] = await Promise.all([getCatalog(), getPrices()]);
  const color = findColor(catalog, decoded);
  if (!color) notFound();

  const siblings = toneSiblings(catalog, color);
  const similar = nearestColors(catalog, color, 10);
  const typeInfo = new Map(catalog.beadTypes.map((t) => [t.key, t]));
  const ink = contrastInk(color.color.hex);

  // Only worth showing when the site says something the catalogue does not:
  // repeating an agreeing classification twice would just be noise.
  const printed = color.finishes.flatMap((f) => [f.finish, f.variation]);
  const officialOnly = (color.official?.finishes ?? []).filter(
    (f) => f && !printed.some((p) => p.includes(f) || f.includes(p)),
  );

  return (
    <article className="pt-6">
      <nav className="mb-5 text-[12px]" style={{ color: "var(--fg-3)" }}>
        <Link href="/">色を探す</Link>
        <span className="mx-1.5">/</span>
        <span className="tabnum" style={{ color: "var(--fg-2)" }}>
          カラーNo.{color.key}
        </span>
      </nav>

      {/* The panel is sized to the artwork rather than the page, so it does not
          leave a wide empty field around a 480px crop. */}
      <header className="grid gap-6 md:grid-cols-[minmax(0,540px)_minmax(0,1fr)]">
        <div
          className="flex items-center justify-center overflow-hidden rounded-xl p-6"
          style={{ background: "var(--swatch-bg)", border: "1px solid var(--line)" }}
        >
          {color.unverified ? (
            <p className="px-6 py-12 text-center text-[12px]" style={{ color: "#8b8379" }}>
              このカラーは誌面から確実な画像を切り出せませんでした。
              <br />
              カタログ P.{color.appearances.map((a) => a.catalogPage).join(" / P.")} をご参照ください。
            </p>
          ) : (
            /* Never scaled past its own pixels: the crops are 480px on their
               long edge, and stretching one across this column softened the
               beads. */
            <img
              src={swatchUrl(color.swatch, color.swatchSource)}
              alt={`カラーNo.${color.key} のビーズ`}
              className="h-auto w-auto max-w-full object-contain"
              style={{ maxHeight: 200 }}
            />
          )}
        </div>

        <div>
          <div className="flex items-baseline gap-3">
            <h1 className="tabnum text-[38px] font-semibold leading-none tracking-tight">
              {color.key}
            </h1>
            <span
              className="rounded-full px-2.5 py-1 text-[11px] font-medium tabnum"
              style={{ background: color.color.hex, color: ink }}
            >
              {color.color.hex}
            </span>
          </div>
          <p className="mt-1 text-[12px]" style={{ color: "var(--fg-3)" }}>
            カラーNo. — 色系統: {color.color.family}
          </p>

          {color.finishes.length > 0 ? (
            <dl className="mt-5 grid gap-3">
              {color.finishes.map((f, i) => (
                <div key={`${f.finish}-${f.variation}-${i}`}>
                  <dt className="text-[11px]" style={{ color: "var(--fg-3)" }}>
                    仕上げ加工
                  </dt>
                  <dd className="text-[15px] font-medium">
                    {f.finish}
                    {f.variation !== f.finish && (
                      <span style={{ color: "var(--fg-2)" }}> — {f.variation}</span>
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="mt-5 text-[13px]" style={{ color: "var(--fg-3)" }}>
              加工区分はカタログの一覧表に記載がありません。
            </p>
          )}

          {color.finishBase && (
            <p className="mt-3 text-[12px]" style={{ color: "var(--fg-3)" }}>
              加工区分は基本カラーNo.{color.finishBase} を継承しています。
            </p>
          )}

          {color.notes.length > 0 && (
            <ul className="mt-4 grid gap-1 text-[12px]" style={{ color: "var(--fg-2)" }}>
              {color.notes.map((n) => (
                <li key={n} className="flex gap-1.5">
                  <span aria-hidden style={{ color: "var(--fg-3)" }}>
                    ・
                  </span>
                  {n}
                </li>
              ))}
            </ul>
          )}

          {color.official && color.official.colorWords.length > 0 && (
            <div className="mt-4">
              <p className="mb-1.5 text-[11px]" style={{ color: "var(--fg-3)" }}>
                色の呼び名
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {color.official.colorWords.map((w) => (
                  <li
                    key={w}
                    className="rounded-full px-2.5 py-1 text-[12px]"
                    style={{ border: "1px solid var(--line)", color: "var(--fg-2)" }}
                  >
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* The 2021 edition and the current site classify a few colours
              differently; both are shown rather than one being picked. */}
          {officialOnly.length > 0 && (
            <p className="mt-4 text-[12px]" style={{ color: "var(--fg-2)" }}>
              公式サイトの加工区分:{" "}
              <span style={{ color: "var(--fg)" }}>{officialOnly.join("・")}</span>
            </p>
          )}

          <p className="mt-5 text-[12px]" style={{ color: "var(--fg-3)" }}>
            掲載ページ: カタログ{" "}
            <span className="tabnum">
              P.{[...new Set(color.appearances.map((a) => a.catalogPage))].join(" / P.")}
            </span>
          </p>
        </div>
      </header>

      {siblings.length > 0 && (
        <Section
          title="同じ基本カラーNo.の濃淡"
          note="カラーNo.のあとに付くL・A・B・C・D・Hは、淡い順から濃い順を表します。"
        >
          <SwatchRow colors={[color, ...siblings]} currentKey={color.key} />
        </Section>
      )}

      {color.official && color.official.shapes.length > 0 && (
        <Section
          title="形状とサイズの比べ方"
          note="トーホー公式サイトの製品写真を、実物の大きさの比率どおりに並べています。丸小と丸大の差がそのまま見た目の差です。"
        >
          {/* Every strip rests on one baseline, so the eye reads the row as a
              size chart: the beads simply grow along it. Boxing each photo would
              hide that, since a box normalises what it contains. */}
          <ul className="flex flex-wrap items-end gap-x-6 gap-y-7">
            {color.official.shapes.map((sh, i) => {
              const h = shapeHeight(sh);
              return (
                <li key={`${sh.category}-${sh.image}-${i}`} className="shrink-0">
                  {/* Cropped to a fixed width rather than scaled down to it —
                      scaling would undo the size difference — and faded at the
                      cut so the strip reads as continuing, not chopped. */}
                  <div
                    className="overflow-hidden rounded-md"
                    style={{
                      background: "var(--swatch-bg)",
                      width: SHAPE_WINDOW,
                      height: h,
                      WebkitMaskImage: SHAPE_FADE,
                      maskImage: SHAPE_FADE,
                    }}
                  >
                    <img
                      src={`/official/${sh.image}`}
                      alt={`${sh.category} No.${color.key}`}
                      loading="lazy"
                      style={{
                        height: h,
                        width: sh.height ? (h * sh.width) / sh.height : SHAPE_WINDOW,
                        maxWidth: "none",
                      }}
                    />
                  </div>
                  <p className="mt-2 text-[12px] leading-tight">
                    <span className="font-medium">{sh.category}</span>
                    {sh.size && (
                      <span className="ml-1.5 tabnum text-[11px]" style={{ color: "var(--fg-3)" }}>
                        {sh.size}mm
                      </span>
                    )}
                  </p>
                </li>
              );
            })}
          </ul>
        </Section>
      )}

      <Section title="このカラーが使われているビーズ">
        <div className="scroll-x">
          <table className="w-full min-w-[640px] border-collapse text-[13px]">
            <thead>
              <tr style={{ color: "var(--fg-3)" }} className="text-left text-[11px]">
                <th className="py-2 pr-4 font-medium">製品ライン</th>
                <th className="py-2 pr-4 font-medium">ビーズ種別・サイズ</th>
                <th className="py-2 pr-4 font-medium">販売スタイル</th>
                <th className="py-2 pr-4 font-medium">カタログ表記</th>
                <th className="py-2 pr-4 font-medium">価格・品番</th>
                <th className="py-2 font-medium">ページ</th>
              </tr>
            </thead>
            <tbody>
              {color.appearances.map((a, i) => (
                <tr key={`${a.catalogPage}-${a.printedAs}-${i}`} style={{ borderTop: "1px solid var(--line)" }}>
                  <td className="py-3 pr-4">{a.line}</td>
                  <td className="py-3 pr-4">
                    <ul className="grid gap-0.5">
                      {a.beadTypes.map((t) => (
                        <li key={t}>
                          {typeInfo.get(t)?.name ?? t}
                          {typeInfo.get(t)?.size && (
                            <span className="ml-1 text-[11px]" style={{ color: "var(--fg-3)" }}>
                              {typeInfo.get(t)!.size}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td className="py-3 pr-4">{a.salesStyle}</td>
                  <td className="py-3 pr-4 tabnum">{a.printedForms.join(" / ")}</td>
                  <td className="py-3 pr-4">
                    {a.variants.length === 0 ? (
                      <span style={{ color: "var(--fg-3)" }}>価格表をご参照ください</span>
                    ) : (
                      <ul className="grid gap-0.5">
                        {a.variants.map((v, vi) => {
                          const live = v.productCode ? prices.prices[v.productCode] : undefined;
                          const yen = live?.price ?? v.price;
                          return (
                            <li key={`${v.productCode ?? vi}`} className="tabnum">
                              {v.style && <span>{v.style} </span>}
                              {v.quantity && (
                                <span style={{ color: "var(--fg-3)" }}>{v.quantity} </span>
                              )}
                              {yen != null && <span className="font-medium">{yen.toLocaleString("ja-JP")}円</span>}
                              {v.productCode && (
                                <span className="ml-1 text-[11px]" style={{ color: "var(--fg-3)" }}>
                                  #{v.productCode}
                                </span>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </td>
                  <td className="py-3 tabnum" style={{ color: "var(--fg-2)" }}>
                    P.{a.catalogPage}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[11px]" style={{ color: "var(--fg-3)" }}>
          {prices.meta.priceKind}・税抜。{catalog.meta.priceNote}
        </p>
      </Section>

      <Section title="色の近いカラー" note="OKLab色空間での距離が近い順に表示しています。">
        <SwatchRow colors={similar} currentKey={color.key} />
      </Section>
    </article>
  );
}

/** How tall to draw a shape's photo so the beads compare at true size. */
function shapeHeight(sh: { category: string; mm: number; height: number }): number {
  const native = sh.height || 60;
  if (LENGTHWISE.some((w) => sh.category.includes(w)) || !sh.mm) {
    return Math.round(native * LENGTHWISE_SCALE);
  }
  return Math.round(Math.min(sh.mm * PX_PER_MM, native * MAX_UPSCALE));
}


function nearestColors(catalog: Catalog, color: BeadColor, n: number): BeadColor[] {
  const target = hexToOklab(color.color.hex);
  return catalog.colors
    .filter((c) => c.key !== color.key)
    .map((c) => ({ c, d: oklabDistance(target, hexToOklab(c.color.hex)) }))
    .sort((a, b) => a.d - b.d)
    .slice(0, n)
    .map((x) => x.c);
}

function Section({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-12">
      <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>
      {note && (
        <p className="mt-1 text-[11.5px]" style={{ color: "var(--fg-3)" }}>
          {note}
        </p>
      )}
      <div className="mt-3">{children}</div>
    </section>
  );
}

function SwatchRow({ colors, currentKey }: { colors: BeadColor[]; currentKey: string }) {
  return (
    <ul className="scroll-x flex gap-3 pb-2">
      {colors.map((c) => {
        const current = c.key === currentKey;
        return (
          <li key={c.key} className="shrink-0">
            <Link
              href={`/colors/${encodeURIComponent(c.key)}`}
              aria-current={current ? "page" : undefined}
              className="block w-[132px] overflow-hidden rounded-[var(--radius-tile)]"
              style={{
                border: `1px solid ${current ? "var(--accent)" : "var(--line)"}`,
                background: "var(--bg-2)",
              }}
            >
              <div
                className="flex aspect-[5/3] items-center justify-center p-2"
                style={{ background: "var(--swatch-bg)" }}
              >
                {c.unverified ? (
                  <span className="text-[10px]" style={{ color: "#8b8379" }}>
                    画像なし
                  </span>
                ) : (
                  <img
                    src={swatchUrl(c.swatch, c.swatchSource)}
                    alt={`カラーNo.${c.key}`}
                    loading="lazy"
                    className="max-h-full max-w-full object-contain"
                  />
                )}
              </div>
              <p className="tabnum px-2 py-1.5 text-[12px] font-medium">
                {c.key}
                {current && (
                  <span className="ml-1 text-[10px]" style={{ color: "var(--accent)" }}>
                    表示中
                  </span>
                )}
              </p>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
