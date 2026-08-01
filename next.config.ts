import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
