import { readFile } from "node:fs/promises";
import path from "node:path";

export type ColorMetrics = {
  hex: string;
  hue: number;
  sat: number;
  val: number;
  family: string;
  appearanceCount?: number;
  spread?: number;
};

export type Variant = {
  style?: string;
  price?: number;
  productCode?: string;
  quantity?: string;
};

export type Appearance = {
  catalogPage: number;
  line: string;
  beadTypes: string[];
  salesStyle: string;
  printedAs: string;
  printedForms: string[];
  linePrefix: string | null;
  swatch: string;
  color: ColorMetrics;
  variants: Variant[];
};

export type FinishRef = { finish: string; variation: string; methods: string[] };

/** What toho-beads.co.jp publishes for this colour. */
export type OfficialInfo = {
  printed: string;
  colorWords: string[];
  finishes: string[];
  shapes: { category: string; size: string; image: string }[];
};

export type BeadColor = {
  key: string;
  number: number;
  suffix: string;
  matte: boolean;
  unverified: boolean;
  finishBase: string | null;
  finishes: FinishRef[];
  notes: string[];
  color: ColorMetrics;
  swatch: string;
  swatchSource: "official" | "catalog";
  official: OfficialInfo | null;
  lines: string[];
  beadTypes: string[];
  salesStyles: string[];
  appearances: Appearance[];
};

export type BeadType = {
  group: string;
  key: string;
  name: string;
  size: string;
  note: string;
};

export type Catalog = {
  meta: {
    title: string;
    edition: string;
    source: string;
    priceNote: string;
    colorCount: number;
    appearanceCount: number;
    pageCount: number;
    droppedAppearances: number;
  };
  finishes: {
    name: string;
    description: string;
    variations: { name: string; methods: string[]; colorNumbers: string[]; note: string | null }[];
  }[];
  methods: { mark: string; name: string; note: string }[];
  beadTypes: BeadType[];
  salesStyles: { key: string; name: string; note: string; pack: string }[];
  lines: { name: string; beadTypes: string[] }[];
  colors: BeadColor[];
};

export type PriceEntry = {
  colorKey: string;
  line: string;
  style: string | null;
  quantity: string | null;
  price: number | null;
  catalogPage: number;
};

export type Prices = {
  meta: {
    note: string;
    currency: string;
    taxIncluded: boolean;
    priceKind: string;
    edition: string;
    codeCount: number;
  };
  prices: Record<string, PriceEntry>;
};

const DATA_DIR = path.join(process.cwd(), "data");

async function readJson<T>(file: string): Promise<T> {
  return JSON.parse(await readFile(path.join(DATA_DIR, file), "utf8")) as T;
}

// Caching the parsed JSON is worth it in production, but in development it would
// mean restarting the server after every price edit — and editing prices is the
// whole point of keeping them in a separate file.
const CACHE = process.env.NODE_ENV === "production";

let catalogCache: Promise<Catalog> | undefined;
let pricesCache: Promise<Prices> | undefined;

export function getCatalog(): Promise<Catalog> {
  if (!CACHE) return readJson<Catalog>("catalog.json");
  catalogCache ??= readJson<Catalog>("catalog.json");
  return catalogCache;
}

/**
 * Prices live in their own file so they can be edited without regenerating the
 * catalogue — the 2021 edition's figures are a starting point, not the truth.
 */
export function getPrices(): Promise<Prices> {
  if (!CACHE) return readJson<Prices>("prices.json");
  pricesCache ??= readJson<Prices>("prices.json");
  return pricesCache;
}

/** The compact record the browse page ships to the client. */
export type ColorIndexEntry = {
  k: string;
  n: number;
  s: string;
  hex: string;
  hue: number;
  sat: number;
  val: number;
  fam: string;
  /** finish variation names, for filtering */
  f: string[];
  /** bead type keys */
  b: string[];
  /** sales styles */
  y: string[];
  sw: string;
  /** "official" images live under /official, catalogue crops under /swatches */
  src: "official" | "catalog";
  matte: boolean;
  /** no crop on any page was clean enough to show */
  unverified: boolean;
};

export function toIndex(colors: BeadColor[]): ColorIndexEntry[] {
  return colors.map((c) => ({
    k: c.key,
    n: c.number,
    s: c.suffix,
    hex: c.color.hex,
    hue: c.color.hue,
    sat: c.color.sat,
    val: c.color.val,
    fam: c.color.family,
    f: c.finishes.map((f) => f.variation),
    b: c.beadTypes,
    y: c.salesStyles,
    sw: c.swatch,
    src: c.swatchSource,
    matte: c.matte,
    unverified: c.unverified,
  }));
}

export function findColor(catalog: Catalog, key: string): BeadColor | undefined {
  return catalog.colors.find((c) => c.key === key);
}

/**
 * Colours that share a base number differ only in tone (5L → 5 → 5D), so they
 * make the most useful "see also" list the catalogue itself implies.
 */
export function toneSiblings(catalog: Catalog, color: BeadColor): BeadColor[] {
  return catalog.colors.filter((c) => c.number === color.number && c.key !== color.key);
}
