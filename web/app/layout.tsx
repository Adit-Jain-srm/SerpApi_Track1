import type { Metadata } from "next";
import localFont from "next/font/local";

import "./globals.css";

const display = localFont({
  src: "../fonts/fraunces-latin.woff2",
  weight: "100 900",
  display: "swap",
  variable: "--font-display",
});

const text = localFont({
  src: [
    {
      path: "../fonts/newsreader-latin.woff2",
      weight: "200 800",
      style: "normal",
    },
    {
      path: "../fonts/newsreader-italic.woff2",
      weight: "200 800",
      style: "italic",
    },
  ],
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
