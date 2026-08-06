import type { MetadataRoute } from "next";

import { siteUrl } from "@/lib/seo";

export const dynamic = "force-static";

// Note that a crawler only reads robots.txt at the origin root, and this file
// lands under the repository sub-path, so on github.io it is advisory at best —
// the sitemap still has to be submitted in Search Console. It costs nothing
// here and becomes the real robots.txt the day the site gets its own domain.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: siteUrl("/sitemap.xml"),
    host: siteUrl("/"),
  };
}
