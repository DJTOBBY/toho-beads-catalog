import type { MetadataRoute } from "next";

import { getCatalog, getRenderedPages } from "@/lib/catalog";
import { catalogPagePath, colorPath, siteUrl } from "@/lib/seo";

// Next writes this straight to out/sitemap.xml with no host of its own to work
// from, so every entry has to be absolute and carry the repository sub-path.
//
// No lastModified anywhere: the only timestamps available at build time are
// checkout times on CI, which would date all 1,100 URLs to the last deploy
// whether or not anything about them changed. Google says it ignores a lastmod
// it finds unreliable, and an unreliable one is all this build can produce.
export const dynamic = "force-static";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [catalog, pages] = await Promise.all([getCatalog(), getRenderedPages()]);

  return [
    { url: siteUrl("/"), changeFrequency: "monthly", priority: 1 },
    { url: siteUrl("/guide/"), changeFrequency: "yearly", priority: 0.8 },
    ...catalog.colors.map((c) => ({
      url: siteUrl(colorPath(c.key)),
      changeFrequency: "yearly" as const,
      priority: 0.7,
    })),
    ...pages.map((n) => ({
      url: siteUrl(catalogPagePath(n)),
      changeFrequency: "yearly" as const,
      priority: 0.4,
    })),
  ];
}
