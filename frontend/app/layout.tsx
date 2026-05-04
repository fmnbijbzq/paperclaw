import type { Metadata } from "next";
import { Atkinson_Hyperlegible, Crimson_Pro } from "next/font/google";

import { AppShell } from "@/components/app-shell";

import "./globals.css";

const bodyFont = Atkinson_Hyperlegible({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "700"],
});

const displayFont = Crimson_Pro({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Paperclaw Console",
  description: "Standalone research operations console for Paperclaw.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${bodyFont.variable} ${displayFont.variable}`}
      suppressHydrationWarning
    >
      <body>
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
