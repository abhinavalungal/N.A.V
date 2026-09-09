import type { Metadata, Viewport } from "next";

import { AppShell } from "@/components/app-shell";

// Fonts are self-hosted from the workspace, not fetched from a font CDN: the
// console has to render identically on a ship's terminal with no internet.
import "@fontsource-variable/ibm-plex-sans";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";

import "./globals.css";

export const metadata: Metadata = {
  title: "N.A.V. - Nautical Agentic Navigator",
  description: "Intelligence for Every Voyage.",
};

export const viewport: Viewport = {
  themeColor: "#06121c",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen font-sans antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
