import type { Metadata, Viewport } from "next";
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

export const viewport: Viewport = {
  themeColor: "#0e1015",
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://serpapi-track1.vercel.app"),
  title: {
    default: "AI Tool Discovery Agent — SerpApi Hackathon Track 1",
    template: "%s — AI Tool Discovery Agent",
  },
  description:
    "Autonomous discovery pipeline for newly launched AI products. Compares SerpApi Google Web and News search engines, validates product homepages, extracts structured metadata via Azure OpenAI, and delivers to Microsoft Teams, Slack, and Supabase subscribers.",
  keywords: [
    "AI Tools",
    "SerpApi",
    "Discovery Pipeline",
    "Azure OpenAI",
    "Slack Webhook",
    "Microsoft Teams Webhook",
    "Supabase",
    "Hackathon",
  ],
  authors: [{ name: "Adit Jain", url: "https://github.com/Adit-Jain-srm" }],
  openGraph: {
    title: "AI Tool Discovery Agent — SerpApi Hackathon Track 1",
    description:
      "Autonomous discovery pipeline for newly launched AI products. Compares SerpApi Google Web and News, extracts structured cards, and broadcasts to Teams and Slack.",
    type: "website",
    locale: "en_US",
    images: [
      {
        url: "/teams_output_example.png",
        width: 1024,
        height: 506,
        alt: "AI Tool Discovery Agent Weekly Digest Card",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "AI Tool Discovery Agent — SerpApi Hackathon Track 1",
    description:
      "Autonomous discovery pipeline for newly launched AI products with SerpApi, Azure OpenAI, Slack, Teams, and Supabase.",
    images: ["/teams_output_example.png"],
  },
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${text.variable}`}>
      <body>{children}</body>
    </html>
  );
}
