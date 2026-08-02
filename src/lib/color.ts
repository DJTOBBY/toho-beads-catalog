/**
 * Perceptual colour distance, used by "この色に近いビーズを探す".
 *
 * sRGB distance ranks badly for this: two pale beads a shopper reads as the same
 * colour can sit further apart in RGB than a red and a brown. OKLab spaces
 * colours roughly the way the eye does, so a plain Euclidean distance in it
 * matches "looks similar" closely enough for browsing.
 */

export type Oklab = { L: number; a: number; b: number };

export function hexToRgb(hex: string): [number, number, number] {
  const v = hex.replace("#", "");
  return [
    parseInt(v.slice(0, 2), 16),
    parseInt(v.slice(2, 4), 16),
    parseInt(v.slice(4, 6), 16),
  ];
}

function srgbToLinear(c: number): number {
  const x = c / 255;
  return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
}

export function rgbToOklab(rgb: [number, number, number]): Oklab {
  const r = srgbToLinear(rgb[0]);
  const g = srgbToLinear(rgb[1]);
  const b = srgbToLinear(rgb[2]);

  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);

  return {
    L: 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    a: 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    b: 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  };
}

export function hexToOklab(hex: string): Oklab {
  return rgbToOklab(hexToRgb(hex));
}

export function oklabDistance(x: Oklab, y: Oklab): number {
  const dL = x.L - y.L;
  const da = x.a - y.a;
  const db = x.b - y.b;
  return Math.sqrt(dL * dL + da * da + db * db);
}

/** A readable text colour for a chip filled with `hex`. */
export function contrastInk(hex: string): string {
  const [r, g, b] = hexToRgb(hex);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum > 0.62 ? "#1b1a19" : "#ffffff";
}

export const HUE_FAMILIES = [
  "レッド",
  "オレンジ",
  "イエロー",
  "グリーン",
  "ブルー",
  "パープル",
  "ピンク",
  "ホワイト",
  "グレー",
  "ブラック",
  "ニュートラル",
] as const;

/** Representative chip colour for each family, for the filter buttons. */
export const FAMILY_SWATCH: Record<string, string> = {
  レッド: "#d0342c",
  オレンジ: "#e8862a",
  イエロー: "#e3cf2a",
  グリーン: "#4f9a52",
  ブルー: "#3b7fc4",
  パープル: "#8a5fb0",
  ピンク: "#d76a97",
  ホワイト: "#f2f0ee",
  グレー: "#9a9a9c",
  ブラック: "#33333a",
  ニュートラル: "#c2b8ac",
};


/** Prefix for files under public/.

    next/link and the bundler pick up basePath on their own, but a plain <img
    src="/…"> does not, and every swatch is one of those. */
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** Where a swatch image is served from, given its source. */
export function swatchUrl(name: string, source: "official" | "catalog"): string {
  return `${BASE_PATH}${source === "official" ? "/official" : "/swatches"}/${name}`;
}

/** URL for one of the official shape photographs. */
export function officialUrl(name: string): string {
  return `${BASE_PATH}/official/${name}`;
}
