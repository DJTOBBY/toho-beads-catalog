/**
 * Drop the segment-cache payloads Next writes beside every exported route.
 *
 * Next 16 emits both the router's own payload (index.txt) and a set of
 * segment-cache files (__next._full.txt, __next._tree.txt, __next.<route>.txt …)
 * for each of the 1,112 routes. The segment cache is off — experimental
 * .cachedNavigations defaults to false — and a network trace of the exported
 * site confirms it: clicking through the colour grid, a colour page, a
 * catalogue page and back only ever fetches index.txt. __next._full.txt is even
 * byte-identical to it.
 *
 * They are not free. They are seven of the nine files in every route directory
 * and about 85 MB of the export, and GitHub Pages publishes by file: the deploy
 * step twice hit the 10-minute ceiling that actions/deploy-pages enforces and
 * cannot be raised past.
 *
 * If a future Next release starts serving navigations from these, client-side
 * navigation would fall back to full page loads rather than break — but the
 * counts printed here are the signal that the assumption needs rechecking.
 */

import { readdir, rm, stat } from "node:fs/promises";
import path from "node:path";

const OUT = path.join(process.cwd(), "out");

// Narrow on purpose: index.html and index.txt cannot match, so this can never
// take a file the site serves.
const PRUNE = /^__next\..*\.txt$/;

let removed = 0;
let freed = 0;
let payloads = 0;

async function walk(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      await walk(full);
      continue;
    }
    if (entry.name === "index.txt") payloads += 1;
    if (!PRUNE.test(entry.name)) continue;
    freed += (await stat(full)).size;
    await rm(full);
    removed += 1;
  }
}

await walk(OUT);

console.log(
  `prune-export: ${removed} ファイル削除（${(freed / 1024 / 1024).toFixed(1)} MB）。` +
    `遷移用ペイロード ${payloads} 件は残しています。`,
);

// The one thing a build can check: that there was still something to prune.
// Nothing to remove means Next's export layout changed and the trace this is
// based on should be run again before trusting these numbers.
if (removed === 0) {
  console.warn("prune-export: 削除対象がありませんでした。Next の出力形式が変わった可能性があります。");
}
