import { NextResponse } from "next/server";

import type { ProofResponse, ProofResult } from "@/lib/types";

/**
 * Live proof for the film. Fixed query only — the request URL is ignored.
 * Azure and Teams secrets are not read here. The only env var is SERPAPI_API_KEY.
 * If that key is unset or the call fails, the film stays on the sample digest.
 */

const QUERY = "new AI tool now available";
const TBS = "qdr:d7";
const NUM = "5";
const HOUR = 3600;

const cacheHeaders = {
  "Cache-Control": `public, max-age=0, s-maxage=${HOUR}, stale-while-revalidate=600`,
};

function sample(reason: string): NextResponse<ProofResponse> {
  return NextResponse.json(
    { source: "sample", query: QUERY, tbs: TBS, results: [], reason },
    { headers: cacheHeaders },
  );
}

let memory: { at: number; body: ProofResponse } | null = null;

function remember(body: ProofResponse) {
  memory = { at: Date.now(), body };
  return NextResponse.json(body, { headers: cacheHeaders });
}

type Organic = {
  title?: unknown;
  link?: unknown;
  snippet?: unknown;
  source?: unknown;
};

function asText(value: unknown, max = 240): string {
  if (typeof value !== "string") return "";
  return value.replace(/\s+/g, " ").trim().slice(0, max);
}

export const dynamic = "force-dynamic";

export async function GET() {
  const key = process.env.SERPAPI_API_KEY;
  if (!key) return sample("SERPAPI_API_KEY unset");

  if (memory && memory.body.source === "live" && Date.now() - memory.at < HOUR * 1000) {
    return NextResponse.json(memory.body, { headers: cacheHeaders });
  }

  const url = new URL("https://serpapi.com/search.json");
  url.searchParams.set("engine", "google");
  url.searchParams.set("q", QUERY);
  url.searchParams.set("tbs", TBS);
  url.searchParams.set("num", NUM);
  url.searchParams.set("hl", "en");
  url.searchParams.set("gl", "us");
  url.searchParams.set("api_key", key);

  try {
    const upstream = await fetch(url, {
      signal: AbortSignal.timeout(12_000),
      next: { revalidate: HOUR },
    });
    if (!upstream.ok) return sample("upstream");

    const body: unknown = await upstream.json();
    const organic = (body as { organic_results?: unknown }).organic_results;
    const rows = Array.isArray(organic) ? organic : [];
    const results: ProofResult[] = [];

    for (const row of rows) {
      if (results.length >= 5) break;
      if (!row || typeof row !== "object") continue;
      const hit = row as Organic;
      const title = asText(hit.title, 180);
      const link = asText(hit.link, 400);
      if (!title || !link) continue;
      results.push({
        title,
        link,
        snippet: asText(hit.snippet, 280),
        source: asText(hit.source, 120),
      });
    }

    return remember({ source: "live", query: QUERY, tbs: TBS, results });
  } catch {
    return sample("upstream");
  }
}
