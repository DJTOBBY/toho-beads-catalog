import { readdir } from "node:fs/promises";
import path from "node:path";

import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCatalog } from "@/lib/catalog";
import { BASE_PATH } from "@/lib/color";

type Params = { params: Promise<{ n: string }> };

/** Catalogue page numbers that render_pages.py has produced an image for. */
async function renderedPages(): Promise<number[]> {
  const dir = path.join(process.cwd(), "public", "pages");
  const files = await readdir(dir);
  return files
    .map((f) => /^p(\d+)\.webp$/.exec(f))
    .filter((m): m is RegExpExecArray => m !== null)
    .map((m) => Number(m[1]))
    .sort((a, b) => a - b);
}

export async function generateStaticParams() {
  return (await renderedPages()).map((n) => ({ n: String(n) }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { n } = await params;
  return {
    title: `カタログ P.${n} | TOHO BEADS カタログ`,
    description: `ビーズカタログ2021 第${Number(n) <= 36 ? 1 : 2}部 ${n}ページの誌面。`,
  };
}

export default async function CatalogPageView({ params }: Params) {
  const { n } = await params;
  const page = Number(n);
  const [pages, catalog] = await Promise.all([renderedPages(), getCatalog()]);
  if (!pages.includes(page)) notFound();

  const i = pages.indexOf(page);
  const prev = pages[i - 1];
  const next = pages[i + 1];

  // Which colours the database placed on this page. The printed page shows
  // numbers only, so this is the way back from the paper into the search.
  const onPage = catalog.colors
    .filter((c) => c.appearances.some((a) => a.catalogPage === page))
    .sort((a, b) => a.number - b.number || a.suffix.localeCompare(b.suffix));

  const lines = [
    ...new Set(
      catalog.colors.flatMap((c) =>
        c.appearances.filter((a) => a.catalogPage === page).map((a) => a.line),
      ),
    ),
  ];

  return (
    <article className="pt-6">
      <nav className="text-[12px]" style={{ color: "var(--fg-3)" }}>
        <Link href="/" style={{ color: "var(--accent)" }}>
          色を探す
        </Link>
        <span className="mx-1.5">/</span>
        <span className="tabnum">カタログ P.{page}</span>
      </nav>

      <header className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-2">
        <h1 className="tabnum text-[28px] font-semibold leading-none tracking-tight">
          P.{page}
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
          src={`${BASE_PATH}/pages/p${page}.webp`}
          alt={`ビーズカタログ2021 ${page}ページ`}
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
