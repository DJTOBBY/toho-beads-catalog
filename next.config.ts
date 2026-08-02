import type { NextConfig } from "next";

// GitHub Pages serves a project repo under /<repo>/, so the app has to know the
// prefix at build time. Empty locally, set by the deploy workflow.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  basePath,
  assetPrefix: basePath || undefined,
  // Every page is generated at build time and nothing runs on a server, so the
  // whole catalogue exports as plain files. That means it can be hosted almost
  // anywhere, and opened from a folder in a pinch.
  output: "export",

  // Swatches are pre-cropped WebP at their final size, so the optimizer would
  // only add work — and the export has no server to run it on anyway.
  images: { unoptimized: true },

  // Static hosts serve /colors/45/ as /colors/45/index.html.
  trailingSlash: true,
};

export default nextConfig;
