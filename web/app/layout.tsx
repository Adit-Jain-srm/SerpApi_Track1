import type { Metadata } from "next";
import { Geist_Mono, Inter_Tight } from "next/font/google";

import "./globals.css";

const display = Inter_Tight({
  subsets: ["latin"],
  weight: ["500", "800"],
  variable: "--font-display",
  display: "swap",
});

const mono = Geist_Mono({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Digest: AI Tool Discovery",
  description:
    "Search noise becomes a weekly digest. A scroll film for the SerpApi Track 1 agent.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
