import { spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ARGS = [
  "-u",
  "main.py",
  "--days",
  "7",
  "--max-urls",
  "6",
  "--skip-teams",
  "--skip-slack",
  "--skip-subscribers",
];
const TIMEOUT_MS = 180_000;

let busy = false;

function repoRoot(): string | null {
  const starts = [process.env.PROJECT_ROOT, process.env.INIT_CWD, process.cwd()].filter(
    (value): value is string => Boolean(value),
  );
  for (const start of starts) {
    let dir = start;
    for (let step = 0; step < 10; step += 1) {
      if (existsSync(join(dir, "main.py")) && existsSync(join(dir, "agents"))) return dir;
      const parent = dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }
  }
  return null;
}

function unavailableMessage(): string {
  if (process.env.VERCEL === "1") {
    return "Hosted Vercel cannot spawn the Python worker. Run the digest from GitHub Actions or the repository CLI.";
  }
  return "The local Python worker was not found. Start the web app from the repository workspace or set PROJECT_ROOT.";
}

function eventStream(body: string, status = 200): Response {
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
    },
  });
}

function pythonBin(root: string): string {
  const windows = join(root, ".venv", "Scripts", "python.exe");
  const unix = join(root, ".venv", "bin", "python");
  if (existsSync(windows)) return windows;
  if (existsSync(unix)) return unix;
  return process.platform === "win32" ? "python" : "python3";
}

function redact(line: string): string {
  return line
    .replace(/xox[baprs]-[A-Za-z0-9-]+/g, "[redacted]")
    .replace(/\bsk-[A-Za-z0-9]{8,}\b/g, "[redacted]")
    .replace(/((?:api[_-]?key|token|secret|password)["']?\s*[:=]\s*["']?)[^\s"']+/gi, "$1[redacted]");
}

function sse(payload: Record<string, unknown>): string {
  return `data: ${JSON.stringify(payload)}\n\n`;
}

export async function POST(request: Request): Promise<Response> {
  const encoder = new TextEncoder();
  if (busy) {
    return new Response(sse({ line: "A run is already in progress." }) + sse({ done: true, code: 1 }), {
      headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
    });
  }

  const root = repoRoot();
  if (!root) {
    return eventStream(sse({ unavailable: true, line: unavailableMessage() }) + sse({ done: true, code: 2 }));
  }

  const origin = request.headers.get("origin");
  if (origin) {
    try {
      if (new URL(origin).host !== request.headers.get("host")) {
        return eventStream(sse({ line: "This run only starts from the site itself." }) + sse({ done: true, code: 1 }), 403);
      }
    } catch {
      return new Response(sse({ done: true, code: 1 }), { status: 400 });
    }
  }

  busy = true;
  let child: ChildProcess | null = null;
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      let settled = false;
      const send = (payload: Record<string, unknown>) => {
        try {
          controller.enqueue(encoder.encode(sse(payload)));
        } catch {
          /* The client closed the stream. */
        }
      };

      send({
        line: "Running main.py --days 7 --max-urls 6 --skip-teams --skip-slack --skip-subscribers",
      });

      const proc = spawn(pythonBin(root), ARGS, {
        cwd: root,
        env: {
          ...process.env,
          PYTHONUNBUFFERED: "1",
          PYTHONIOENCODING: "utf-8",
        },
        windowsHide: true,
      });
      child = proc;

      let leftover = "";
      const push = (chunk: Buffer) => {
        leftover += chunk.toString("utf8");
        const parts = leftover.split(/\r?\n/);
        leftover = parts.pop() ?? "";
        for (const part of parts) {
          const line = redact(part);
          if (line.trim()) send({ line: line.slice(0, 500) });
        }
      };

      proc.stdout?.on("data", push);
      proc.stderr?.on("data", push);

      const timer = setTimeout(() => {
        send({ line: "Stopped after 3 minutes." });
        proc.kill();
      }, TIMEOUT_MS);

      const finish = (code: number) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (leftover.trim()) send({ line: redact(leftover).slice(0, 500) });
        send({ done: true, code });
        busy = false;
        try {
          controller.close();
        } catch {
          /* Already closed. */
        }
      };

      proc.on("error", (error) => {
        send({ line: error.message });
        proc.kill();
      });
      proc.on("close", (code) => finish(code ?? 1));

      const stop = () => {
        proc.kill();
      };
      request.signal.addEventListener("abort", stop);
    },
    cancel() {
      child?.kill();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no",
    },
  });
}
