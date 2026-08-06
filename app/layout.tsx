import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import "./globals.css";
import { ThemeToggle } from "@/components/ThemeToggle";
import { getCatalog } from "@/lib/catalog";
import { BRAND, OG_IMAGE, SITE_NAME, SITE_URL, siteUrl } from "@/lib/seo";

// The colour count is read rather than written down: it has already gone stale
// once here, and the pipeline changes it every time a line is added.
export async function generateMetadata(): Promise<Metadata> {
  const catalog = await getCatalog();
  const description =
    `${BRAND}のグラスビーズカタログ。カラーNo.・品番・仕上げ加工・ビーズ種別、` +
    `そして色そのものから${catalog.meta.colorCount}色を検索できます。`;

  return {
    // Only a fallback for the resolvers; every route sets its own absolute URLs.
    metadataBase: new URL(`${SITE_URL}/`),
    title: `${SITE_NAME} | ガラスビーズを色から探す`,
    description,
    applicationName: SITE_NAME,
    // Large image previews and untruncated snippets are opt-in, and a catalogue
    // of photographs has little to show without them.
    robots: {
      index: true,
      follow: true,
      googleBot: { index: true, follow: true, "max-image-preview": "large", "max-snippet": -1 },
    },
    openGraph: {
      type: "website",
      locale: "ja_JP",
      siteName: SITE_NAME,
      url: siteUrl("/"),
      images: [OG_IMAGE],
    },
    twitter: { card: "summary_large_image", images: [OG_IMAGE.url] },
  };
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja" suppressHydrationWarning>
      <body style={{ background: "var(--bg)", color: "var(--fg)" }}>
        {/* Runs before hydration so a saved dark theme does not flash the light
            palette on the way in. */}
        <Script id="theme-init" strategy="beforeInteractive">
          {`try{var t=localStorage.getItem("toho-theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}`}
        </Script>
        <header
          className="sticky top-0 z-30 backdrop-blur-md"
          style={{
            background: "color-mix(in srgb, var(--bg) 86%, transparent)",
            borderBottom: "1px solid var(--line)",
          }}
        >
          <div className="mx-auto flex max-w-[1400px] items-center gap-4 px-4 py-3 sm:px-6">
            {/* shrink-0 + nowrap throughout: without them a narrow viewport
                squeezes the Japanese labels into vertical strips. */}
            <Link href="/" className="flex shrink-0 items-baseline gap-2 whitespace-nowrap">
              <span className="text-[17px] font-semibold tracking-tight">TOHO BEADS</span>
              <span className="hidden text-[11px] sm:inline" style={{ color: "var(--fg-3)" }}>
                カタログ
              </span>
            </Link>
            <nav className="ml-auto flex shrink-0 items-center gap-1 whitespace-nowrap text-[13px]">
              <Link
                href="/"
                className="shrink-0 rounded-full px-2.5 py-1.5 transition-colors sm:px-3"
                style={{ color: "var(--fg-2)" }}
              >
                色を探す
              </Link>
              <Link
                href="/guide"
                className="shrink-0 rounded-full px-2.5 py-1.5 transition-colors sm:px-3"
                style={{ color: "var(--fg-2)" }}
              >
                加工と形状
              </Link>
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] px-4 pb-24 sm:px-6">{children}</main>
        <footer
          className="mx-auto max-w-[1400px] px-4 py-10 text-[12px] sm:px-6"
          style={{ color: "var(--fg-3)", borderTop: "1px solid var(--line)" }}
        >
          <p>
            掲載データは「ビーズカタログ2021（第1部・第2部）」に基づき、色見本の写真は
            トーホー公式サイト（toho-beads.co.jp）の製品画像を使用しています。ガラス特有の光沢や質感、
            微妙な色合いは、写真・印刷・画面表示により実物とは異なる場合があります。
          </p>
          <p className="mt-2">
            価格は変更される場合があります。最新の価格・在庫はお問い合わせください。
          </p>
        </footer>
      </body>
    </html>
  );
}
