import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { NextResponse } from "next/server";

import { validateWebhookUrl } from "@/lib/url-safety";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function repoRoot(): string | null {
  let dir = process.cwd();
  for (let step = 0; step < 5; step += 1) {
    if (existsSync(join(dir, "main.py")) && existsSync(join(dir, "agents"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

type ServiceResult = {
  status: "pass" | "warn" | "fail";
  latencyMs: number;
  message: string;
  subscribers?: number;
  searchesLeft?: number;
};

export async function GET() {
  const started = Date.now();
  const root = repoRoot();
  const supaUrl = (process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || "").trim().replace(/\/$/, "");
  const supaKey = (process.env.SUPABASE_SECRET_KEY || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || "").trim();
  let supabaseResult: ServiceResult = { status: "fail", latencyMs: 0, message: "Unconfigured" };

  if (supaUrl && supaKey) {
    const t0 = Date.now();
    try {
      const resp = await fetch(`${supaUrl}/rest/v1/subscriptions?select=user_id`, {
        headers: {
          apikey: supaKey,
          Authorization: `Bearer ${supaKey}`,
          Prefer: "count=exact",
        },
        cache: "no-store",
      });
      const latency = Date.now() - t0;
      if (resp.ok) {
        const range = resp.headers.get("content-range") || "";
        const count = range.includes("/") ? parseInt(range.split("/")[1], 10) : 0;
        supabaseResult = {
          status: "pass",
          latencyMs: latency,
          message: `Connected (${latency}ms) — subscriptions table active`,
          subscribers: Number.isNaN(count) ? 0 : count,
        };
      } else {
        supabaseResult = { status: "warn", latencyMs: latency, message: `Supabase returned HTTP ${resp.status}` };
      }
    } catch (err: unknown) {
      supabaseResult = {
        status: "fail",
        latencyMs: Date.now() - t0,
        message: err instanceof Error ? err.message : "Connection failed",
      };
    }
  }

  const serpKey = (process.env.SERPAPI_API_KEY || "").trim();
  let serpapiResult: ServiceResult = { status: "fail", latencyMs: 0, message: "SERPAPI_API_KEY missing" };
  if (serpKey) {
    const t0 = Date.now();
    try {
      const resp = await fetch(`https://serpapi.com/account?api_key=${encodeURIComponent(serpKey)}`, {
        cache: "no-store",
      });
      const latency = Date.now() - t0;
      if (resp.ok) {
        const data = await resp.json();
        serpapiResult = {
          status: "pass",
          latencyMs: latency,
          message: `Verified (${latency}ms) — ${data.total_searches_left ?? "active"} searches remaining`,
          searchesLeft: data.total_searches_left,
        };
      } else {
        serpapiResult = { status: "warn", latencyMs: latency, message: `SerpApi returned HTTP ${resp.status}` };
      }
    } catch (err: unknown) {
      serpapiResult = {
        status: "fail",
        latencyMs: Date.now() - t0,
        message: err instanceof Error ? err.message : "Fetch failed",
      };
    }
  }

  const pipelineResult = {
    status: root ? ("pass" as const) : ("warn" as const),
    message: root ? "Python execution engine available" : "Python engine path not found on host",
    hasRoot: Boolean(root),
  };
  const allPass = supabaseResult.status === "pass" && serpapiResult.status === "pass" && pipelineResult.status === "pass";

  return NextResponse.json({
    status: allPass ? "operational" : "degraded",
    uptimeSeconds: process.uptime(),
    responseTimeMs: Date.now() - started,
    timestamp: new Date().toISOString(),
    services: { supabase: supabaseResult, serpapi: serpapiResult, pipeline: pipelineResult },
  });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    let current = await validateWebhookUrl(typeof body?.url === "string" ? body.url : "");
    const testPayload = {
      text: "⚡ **AI Tool Discovery Agent Test Ping**\nYour webhook was successfully verified.",
    };

    let response: Response | undefined;
    for (let hop = 0; hop <= 3; hop += 1) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      try {
        response = await fetch(current, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testPayload),
          redirect: "manual",
          signal: controller.signal,
        });
      } finally {
        clearTimeout(timeout);
      }
      if (![301, 302, 303, 307, 308].includes(response.status)) break;
      const location = response.headers.get("location");
      if (!location) break;
      current = await validateWebhookUrl(new URL(location, current).toString());
    }

    if (!response) throw new Error("Webhook did not return a response.");
    if (response.ok || response.status === 204) {
      return NextResponse.json({ ok: true, status: response.status, message: "Webhook ping received successfully!" });
    }
    const text = await response.text().catch(() => "");
    return NextResponse.json(
      { ok: false, status: response.status, error: `Webhook returned HTTP ${response.status}: ${text.slice(0, 100)}` },
      { status: 400 },
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: err instanceof Error ? err.message : "Failed to ping webhook" },
      { status: 400 },
    );
  }
}
