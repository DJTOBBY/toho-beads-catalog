"use client";

import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";
import type { ColorIndexEntry } from "@/lib/catalog";
import { FAMILY_SWATCH, hexToOklab, oklabDistance } from "@/lib/color";

type Props = {
  colors: ColorIndexEntry[];
  finishGroups: { finish: string; variations: string[] }[];
  beadGroups: { group: string; types: { key: string; name: string }[] }[];
  salesStyles: string[];
  /** colour number -> product codes, so the search box also matches 品番. */
  codeIndex: Record<string, string>;
};

type Sort = "number" | "hue" | "light" | "match";

const SORTS: { id: Sort; label: string }[] = [
  { id: "number", label: "カラーNo." },
  { id: "hue", label: "色相順" },
  { id: "light", label: "明るい順" },
];

export function CatalogBrowser({
  colors,
  finishGroups,
  beadGroups,
  salesStyles,
  codeIndex,
}: Props) {
  const [query, setQuery] = useState("");
  const [families, setFamilies] = useState<Set<string>>(new Set());
  const [finishes, setFinishes] = useState<Set<string>>(new Set());
  const [beadTypes, setBeadTypes] = useState<Set<string>>(new Set());
  const [styles, setStyles] = useState<Set<string>>(new Set());
  const [matteOnly, setMatteOnly] = useState(false);
  const [pickedColor, setPickedColor] = useState<string | null>(null);
  const [sort, setSort] = useState<Sort>("number");
  const [limit, setLimit] = useState(240);

  const deferredQuery = useDeferredValue(query);

  // Precompute OKLab once; recomputing per keystroke over ~940 colours is
  // wasteful and shows up as jank on the colour slider.
  const labs = useMemo(
    () => new Map(colors.map((c) => [c.k, hexToOklab(c.hex)])),
    [colors],
  );

  const familyCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const c of colors) m.set(c.fam, (m.get(c.fam) ?? 0) + 1);
    return m;
  }, [colors]);

  const results = useMemo(() => {
    const q = deferredQuery.trim().toUpperCase().replace(/\s+/g, "");
    let out = colors.filter((c) => {
      if (families.size && !families.has(c.fam)) return false;
      if (finishes.size && !c.f.some((f) => finishes.has(f))) return false;
      if (beadTypes.size && !c.b.some((b) => beadTypes.has(b))) return false;
      if (styles.size && !c.y.some((y) => styles.has(y))) return false;
      if (matteOnly && !c.matte) return false;
      if (q) {
        const inKey = c.k.includes(q);
        const inCode = (codeIndex[c.k] ?? "").includes(q);
        const inFinish = c.f.some((f) => f.toUpperCase().includes(q));
        if (!inKey && !inCode && !inFinish) return false;
      }
      return true;
    });

    if (pickedColor) {
      const target = hexToOklab(pickedColor);
      out = out
        .map((c) => ({ c, d: oklabDistance(target, labs.get(c.k)!) }))
        .sort((a, b) => a.d - b.d)
        .map((x) => x.c);
    } else if (sort === "hue") {
      out = [...out].sort((a, b) => a.hue - b.hue || b.sat - a.sat);
    } else if (sort === "light") {
      out = [...out].sort((a, b) => b.val - a.val);
    } else {
      out = [...out].sort((a, b) => a.n - b.n || a.s.localeCompare(b.s));
    }
    return out;
  }, [
    colors,
    deferredQuery,
    families,
    finishes,
    beadTypes,
    styles,
    matteOnly,
    pickedColor,
    sort,
    labs,
    codeIndex,
  ]);

  const visible = results.slice(0, limit);
  const activeFilters =
    families.size + finishes.size + beadTypes.size + styles.size + (matteOnly ? 1 : 0);

  function toggle(set: Set<string>, apply: (s: Set<string>) => void, value: string) {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    apply(next);
    setLimit(240);
  }

  function reset() {
    setQuery("");
    setFamilies(new Set());
    setFinishes(new Set());
    setBeadTypes(new Set());
    setStyles(new Set());
    setMatteOnly(false);
    setPickedColor(null);
    setSort("number");
    setLimit(240);
  }

  return (
    <div className="grid gap-6 pt-6 lg:grid-cols-[268px_1fr] lg:gap-8">
      <aside className="lg:sticky lg:top-[68px] lg:self-start">
        <div className="grid gap-5">
          <Field label="カラーNo. / 品番で検索">
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setLimit(240);
              }}
              placeholder="例: 2113 / 741911 / 46L"
              inputMode="search"
              className="w-full rounded-lg px-3 py-2 text-[14px] outline-none tabnum"
              style={{
                background: "var(--bg-2)",
                border: "1px solid var(--line)",
                color: "var(--fg)",
              }}
            />
          </Field>

          <Field label="色から探す">
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="color"
                aria-label="探したい色を選ぶ"
                value={pickedColor ?? "#c0392b"}
                onChange={(e) => {
                  setPickedColor(e.target.value);
                  setSort("match");
                  setLimit(120);
                }}
                className="h-9 w-14 shrink-0 cursor-pointer rounded-lg"
                style={{ border: "1px solid var(--line)", background: "var(--bg-2)" }}
              />
              {pickedColor ? (
                <button
                  type="button"
                  onClick={() => {
                    setPickedColor(null);
                    setSort("number");
                  }}
                  className="shrink-0 whitespace-nowrap rounded-full px-2.5 py-1 text-[11px]"
                  style={{ border: "1px solid var(--line)", color: "var(--fg-2)" }}
                >
                  色で並べるのを解除
                </button>
              ) : (
                <p className="text-[11px] leading-snug" style={{ color: "var(--fg-3)" }}>
                  選んだ色に近い順に並べ替えます
                </p>
              )}
            </div>
          </Field>

          <Field label="色系統">
            <div className="flex flex-wrap gap-1.5">
              {[...familyCounts.entries()]
                .sort((a, b) => b[1] - a[1])
                .map(([fam, count]) => {
                  const on = families.has(fam);
                  return (
                    <button
                      key={fam}
                      type="button"
                      onClick={() => toggle(families, setFamilies, fam)}
                      aria-pressed={on}
                      className="flex items-center gap-1.5 rounded-full py-1 pl-1.5 pr-2.5 text-[12px] transition-colors"
                      style={{
                        border: `1px solid ${on ? "var(--accent)" : "var(--line)"}`,
                        background: on ? "var(--accent-soft)" : "transparent",
                        color: "var(--fg-2)",
                      }}
                    >
                      <span
                        aria-hidden
                        className="size-3 rounded-full"
                        style={{
                          background: FAMILY_SWATCH[fam] ?? "#bbb",
                          boxShadow: "inset 0 0 0 1px rgba(0,0,0,.12)",
                        }}
                      />
                      {fam}
                      <span className="tabnum" style={{ color: "var(--fg-3)" }}>
                        {count}
                      </span>
                    </button>
                  );
                })}
            </div>
          </Field>

          <Details label={`仕上げ加工${finishes.size ? ` (${finishes.size})` : ""}`}>
            <div className="grid gap-3">
              {finishGroups.map((g) => (
                <div key={g.finish}>
                  <p className="mb-1 text-[11px]" style={{ color: "var(--fg-3)" }}>
                    {g.finish}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {g.variations.map((v) => (
                      <Chip
                        key={v}
                        on={finishes.has(v)}
                        onClick={() => toggle(finishes, setFinishes, v)}
                      >
                        {v}
                      </Chip>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Details>

          <Details label={`ビーズ種別${beadTypes.size ? ` (${beadTypes.size})` : ""}`}>
            <div className="grid gap-3">
              {beadGroups.map((g) => (
                <div key={g.group}>
                  <p className="mb-1 text-[11px]" style={{ color: "var(--fg-3)" }}>
                    {g.group}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {g.types.map((t) => (
                      <Chip
                        key={t.key}
                        on={beadTypes.has(t.key)}
                        onClick={() => toggle(beadTypes, setBeadTypes, t.key)}
                      >
                        {t.key}
                      </Chip>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Details>

          <Field label="販売スタイル">
            <div className="flex flex-wrap gap-1.5">
              {salesStyles.map((s) => (
                <Chip key={s} on={styles.has(s)} onClick={() => toggle(styles, setStyles, s)}>
                  {s}
                </Chip>
              ))}
              <Chip on={matteOnly} onClick={() => setMatteOnly(!matteOnly)}>
                つや消し(F)のみ
              </Chip>
            </div>
          </Field>

          {(activeFilters > 0 || query || pickedColor) && (
            <button
              type="button"
              onClick={reset}
              className="justify-self-start rounded-full px-3 py-1.5 text-[12px]"
              style={{ border: "1px solid var(--accent)", color: "var(--accent)" }}
            >
              条件をすべて解除
            </button>
          )}
        </div>
      </aside>

      <section>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <p className="text-[13px]" style={{ color: "var(--fg-2)" }}>
            <span className="tabnum text-[17px] font-semibold" style={{ color: "var(--fg)" }}>
              {results.length}
            </span>
            <span className="ml-1">色</span>
            {pickedColor && <span className="ml-2">・選んだ色に近い順</span>}
          </p>
          {!pickedColor && (
            <div className="ml-auto flex items-center gap-1" role="group" aria-label="並び順">
              {SORTS.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setSort(s.id)}
                  aria-pressed={sort === s.id}
                  className="rounded-full px-2.5 py-1 text-[12px]"
                  style={{
                    border: `1px solid ${sort === s.id ? "var(--accent)" : "var(--line)"}`,
                    background: sort === s.id ? "var(--accent-soft)" : "transparent",
                    color: "var(--fg-2)",
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {results.length === 0 ? (
          <p className="py-16 text-center text-[14px]" style={{ color: "var(--fg-3)" }}>
            条件に合うビーズが見つかりませんでした。条件を減らしてお試しください。
          </p>
        ) : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5">
            {visible.map((c) => (
              <li key={c.k}>
                <Link
                  href={`/colors/${encodeURIComponent(c.k)}`}
                  className="group block overflow-hidden rounded-[var(--radius-tile)] transition-shadow"
                  style={{ border: "1px solid var(--line)", background: "var(--bg-2)" }}
                >
                  <div
                    className="flex aspect-[5/3] items-center justify-center overflow-hidden p-2"
                    style={{ background: "var(--swatch-bg)" }}
                  >
                    {c.unverified ? (
                      <span
                        className="text-[10px]"
                        style={{ color: "#8b8379" }}
                        title="この色は誌面から確実な画像を切り出せませんでした"
                      >
                        画像なし
                      </span>
                    ) : (
                      <img
                        src={`/swatches/${c.sw}`}
                        alt={`カラーNo.${c.k} のビーズ`}
                        loading="lazy"
                        decoding="async"
                        className="max-h-full max-w-full object-contain"
                      />
                    )}
                  </div>
                  <div className="flex items-center gap-2 px-2.5 py-2">
                    <span
                      aria-hidden
                      className="size-3.5 shrink-0 rounded-full"
                      style={{
                        background: c.hex,
                        boxShadow: "inset 0 0 0 1px rgba(0,0,0,.15)",
                      }}
                    />
                    <span className="tabnum text-[14px] font-semibold">{c.k}</span>
                    <span
                      className="ml-auto truncate text-[10.5px]"
                      style={{ color: "var(--fg-3)" }}
                      title={c.f.join("・")}
                    >
                      {c.f[0] ?? "—"}
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}

        {visible.length < results.length && (
          <div className="mt-8 flex justify-center">
            <button
              type="button"
              onClick={() => setLimit((n) => n + 240)}
              className="rounded-full px-5 py-2 text-[13px]"
              style={{ border: "1px solid var(--line)", color: "var(--fg-2)" }}
            >
              さらに表示（残り {results.length - visible.length} 色）
            </button>
          </div>
        )}
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1.5 text-[11px] font-semibold tracking-wide" style={{ color: "var(--fg-3)" }}>
        {label}
      </p>
      {children}
    </div>
  );
}

function Details({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <details className="group">
      <summary
        className="cursor-pointer list-none text-[11px] font-semibold tracking-wide"
        style={{ color: "var(--fg-3)" }}
      >
        {label}
        <span className="ml-1 inline-block transition-transform group-open:rotate-90">›</span>
      </summary>
      <div className="mt-2">{children}</div>
    </details>
  );
}

function Chip({
  on,
  onClick,
  children,
}: {
  on: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      className="rounded-full px-2.5 py-1 text-[12px] transition-colors"
      style={{
        border: `1px solid ${on ? "var(--accent)" : "var(--line)"}`,
        background: on ? "var(--accent-soft)" : "transparent",
        color: on ? "var(--fg)" : "var(--fg-2)",
      }}
    >
      {children}
    </button>
  );
}
