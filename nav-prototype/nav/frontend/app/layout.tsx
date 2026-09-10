import type { Metadata } from "next";

import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";

import { TopNav } from "@/components/nav/TopNav";

import "./globals.css";

export const metadata: Metadata = {
  title: "N.A.V. — Nautical Agentic Navigator",
  description: "Intelligence for Every Voyage. Maritime voyage optimization prototype.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-abyss">
        <TopNav />
        <main className="mx-auto w-full max-w-[1760px] px-5 py-5">{children}</main>
      </body>
    </html>
  );
}
