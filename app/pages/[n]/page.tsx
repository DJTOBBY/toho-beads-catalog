import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { JsonLd } from "@/components/JsonLd";
import { getCatalog, getRenderedPages } from "@/lib/catalog";
import { BASE_PATH, catalogPageImagePath } from "@/lib/color";
import { imageSize } from "@/lib/imageSize";
import {
  BRAND,
  breadcrumbJsonLd,
  catalogPageJsonLd,
  catalogPagePath,
  pageMetadata,
  siteUrl,
} from "@/lib/seo";

type Params = { params: Promise<{ n: string }> };

export async function generateStaticParams() {
  return (await getRenderedPages()).map((n) => ({ n: String(n) }));
}

/** Which colours the database placed on a printed page, in catalogue order. */
function colorsOnPage(catalog: Awaited<ReturnType<typeof getCatalog>>, page: number) {
  return catalog.colors
    .filter((c) => c.appearances.some((a) => a.catalogPage === page))
    .sort((a, b) => a.number - b.number || a.suffix.localeCompare(b.suffix));
}

function linesOnPage(catalog: Awaited<ReturnType<typeof getCatalog>>, page: number) {
  return [
    ...new Set(
      catalog.colors.flatMap((c) =>
        c.appearances.filter((a) => a.catalogPage === page).map((a) => a.line),
      ),
    ),
  ];
}

// 72 scans of the same catalogue would otherwise differ only by a number, so the
// product lines and the colour numbers printed on each page carry the text.
export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { n } = await params;
  const page = Number(n);
  const catalog = await getCatalog();
  const lines = linesOnPage(catalog, page);
  const keys = colorsOnPage(catalog, page).map((c) => c.key);

  // meta.source names both volumes ("… 第1部・第2部"), which is more than a title
  // has room for; the edition alone is what a reader recognises.
  const work = catalog.meta.source.split(" ")[0];
  const headline = lines.slice(0, 2).join("・") + (lines.length > 2 ? "ほか" : "");

  return pageMetadata({
    path: catalogPagePath(page),
    title: `${work} P.${page}${headline ? `｜${headline}` : ""} | ${BRAND}`,
    description:
      `${catalog.meta.source} ${page}ページの誌面。` +
      (lines.length ? `掲載は${lines.join("・")}。` : "") +
      (keys.length
        ? `カラーNo.${keys.slice(0, 8).join("・")}${keys.length > 8 ? `ほか計${keys.length}色` : ""}が載っています。`
        : ""),
  });
}

export default async function CatalogPageView({ params }: Params) {
  const { n } = await params;
  const page = Number(n);
  const [pages, catalog] = await Promise.all([getRenderedPages(), getCatalog()]);
  if (!pages.includes(page)) notFound();

  const i = pages.indexOf(page);
  const prev = pages[i - 1];
  const next = pages[i + 1];

  // Which colours the database placed on this page. The printed page shows
  // numbers only, so this is the way back from the paper into the search.
  const onPage = colorsOnPage(catalog, page);
  const lines = linesOnPage(catalog, page);

  const scan = catalogPageImagePath(page);
  // The scan is the tallest thing on the page; without its ratio the colour
  // list below it jumps down the moment the image lands.
  const scanBox = await imageSize(scan);

  return (
    <article className="pt-6">
      <JsonLd
        data={catalogPageJsonLd({
          page,
          image: siteUrl(scan),
          description: `${catalog.meta.source} ${page}ページの誌面と、そこに掲載されているカラー${onPage.length}色。`,
          colorKeys: onPage.map((c) => c.key),
          source: catalog.meta.source,
        })}
      />
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "色を探す", path: "/" },
          { name: `カタログ P.${page}`, path: catalogPagePath(page) },
        ])}
      />
      <nav className="text-[12px]" style={{ color: "var(--fg-3)" }}>
        <Link href="/" style={{ color: "var(--accent)" }}>
          色を探す
        </Link>
        <span className="mx-1.5">/</span>
        <span className="tabnum">カタログ P.{page}</span>
      </nav>

      <header className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-2">
        <h1 className="tabnum text-[28px] font-semibold leading-none tracking-tight">
          <span className="sr-only">{catalog.meta.source} </span>P.{page}
        </h1>
        <p className="text-[13px]" style={{ color: "var(--fg-2)" }}>
          {lines.length > 0 ? lines.join("・") : catalog.meta.source}
        </p>
        <div className="ml-auto flex items-center gap-1.5 text-[13px]">
          <Pager to={prev} label="← 前のページ" />
          <Pager to={next} label="次のページ →" />
        </div>
      </header>

      {/* The scan is 1600px wide; capping it keeps the type at the size it was
          printed to be read at rather than blowing it up to the viewport. */}
      <figure
        className="mt-5 overflow-hidden rounded-xl"
        style={{ border: "1px solid var(--line)", background: "var(--swatch-bg)" }}
      >
        <img
          src={`${BASE_PATH}${scan}`}
          alt={`${catalog.meta.source} ${page}ページの誌面${lines.length ? `（${lines.join("・")}）` : ""}`}
          width={scanBox?.width}
          height={scanBox?.height}
          fetchPriority="high"
          className="mx-auto block h-auto w-full"
          style={{ maxWidth: 1100 }}
        />
      </figure>

      {onPage.length > 0 && (
        <section className="mt-10">
          <h2 className="text-[15px] font-semibold tracking-tight">
            このページに載っているカラー
            <span className="tabnum ml-2 text-[13px] font-normal" style={{ color: "var(--fg-3)" }}>
              {onPage.length}色
            </span>
          </h2>
          <ul className="mt-3 flex flex-wrap gap-1.5">
            {onPage.map((c) => (
              <li key={c.key}>
                <Link
                  href={`/colors/${encodeURIComponent(c.key)}`}
                  className="flex items-center gap-1.5 rounded-full py-1 pl-1.5 pr-2.5 text-[12px]"
                  style={{ border: "1px solid var(--line)", color: "var(--fg-2)" }}
                >
                  <span
                    aria-hidden
                    className="size-3.5 shrink-0 rounded-full"
                    style={{
                      background: c.color.hex,
                      boxShadow: "inset 0 0 0 1px rgba(0,0,0,.15)",
                    }}
                  />
                  <span className="tabnum">{c.key}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="mt-10 text-[11.5px]" style={{ color: "var(--fg-3)" }}>
        {catalog.meta.source}（{catalog.meta.edition}）の誌面です。
        価格は誌面発行時のもので、最新の価格は各カラーのページをご確認ください。
      </p>
    </article>
  );
}

function Pager({ to, label }: { to: number | undefined; label: string }) {
  if (to === undefined) {
    return (
      <span
        className="rounded-full px-3 py-1.5"
        style={{ border: "1px solid var(--line)", color: "var(--fg-3)", opacity: 0.5 }}
      >
        {label}
      </span>
    );
  }
  return (
    <Link
      href={`/pages/${to}/`}
      className="rounded-full px-3 py-1.5"
      style={{ border: "1px solid var(--line)", color: "var(--fg-2)" }}
    >
      {label}
    </Link>
  );
}
