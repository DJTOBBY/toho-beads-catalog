import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Swatches are pre-cropped WebP at their final size, so the optimizer would
  // only add work. Everything else still goes through next/image.
  images: { unoptimized: true },
};

export default nextConfig;
