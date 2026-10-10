import type { Metadata } from "next";
import { Fraunces, Newsreader } from "next/font/google";

import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
  axes: ["opsz", "SOFT", "WONK"],
});

const text = Newsreader({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  display: "swap",
  variable: "--font-text",
});

export const metadata: Metadata = {
  title: "AI Tool Discovery Agent",
  description:
    "It searches SerpApi for newly launched AI tools and posts a card to the console, Microsoft Teams, and Slack.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${text.variable}`}>
      <body>{children}</body>
    </html>
  );
}
