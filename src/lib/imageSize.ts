/**
 * Intrinsic size of a WebP file under public/, read at build time.
 *
 * Every photograph on the site is a WebP of a size only the file knows, and an
 * <img> without width and height reflows the page the moment it loads. Reading
 * the header here lets the markup reserve the right box, which is the whole of
 * the CLS problem on the colour and catalogue-page views.
 */

import { open } from "node:fs/promises";
import path from "node:path";

export type ImageSize = { width: number; height: number };

const PUBLIC_DIR = path.join(process.cwd(), "public");

// The three WebP variants put the dimensions in different places, all within
// the first 30 bytes, so the header is all that ever gets read.
const HEADER_BYTES = 32;

function parse(buf: Buffer): ImageSize | null {
  if (buf.length < 30) return null;
  if (buf.toString("ascii", 0, 4) !== "RIFF") return null;
  if (buf.toString("ascii", 8, 12) !== "WEBP") return null;

  switch (buf.toString("ascii", 12, 16)) {
    // Extended format: 24-bit canvas width and height, each stored minus one.
    case "VP8X":
      return {
        width: (buf[24] | (buf[25] << 8) | (buf[26] << 16)) + 1,
        height: (buf[27] | (buf[28] << 8) | (buf[29] << 16)) + 1,
      };
    // Lossless: 14 bits each, minus one, packed little-endian after the signature.
    case "VP8L": {
      const bits = buf.readUInt32LE(21);
      return { width: (bits & 0x3fff) + 1, height: ((bits >> 14) & 0x3fff) + 1 };
    }
    // Lossy: 14 bits each after the 3-byte start code, the top two bits being scale.
    case "VP8 ":
      return {
        width: buf.readUInt16LE(26) & 0x3fff,
        height: buf.readUInt16LE(28) & 0x3fff,
      };
    default:
      return null;
  }
}

// 1,036 colour pages plus 72 catalogue pages each ask for a handful of files,
// and many colours share a swatch, so the answers are worth keeping.
const cache = new Map<string, ImageSize | null>();

/** Size of a file under public/, or null when it cannot be read. */
export async function imageSize(publicPath: string): Promise<ImageSize | null> {
  const cached = cache.get(publicPath);
  if (cached !== undefined) return cached;

  let size: ImageSize | null = null;
  try {
    const file = await open(path.join(PUBLIC_DIR, publicPath), "r");
    try {
      const buf = Buffer.alloc(HEADER_BYTES);
      const { bytesRead } = await file.read(buf, 0, HEADER_BYTES, 0);
      size = parse(buf.subarray(0, bytesRead));
    } finally {
      await file.close();
    }
  } catch {
    size = null;
  }

  cache.set(publicPath, size);
  return size;
}
