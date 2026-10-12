"use client";

import { useEffect, useRef, useState } from "react";

type Phase = "idle" | "running" | "done" | "error" | "unavailable";

const GITHUB_ACTIONS_HREF =
  "https://github.com/Adit-Jain-srm/SerpApi_Track1/actions/workflows/weekly-digest.yml";

export function RunDrawer() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [lines, setLines] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const logRef = useRef<HTMLPreElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const runningRef = useRef(false);
  const timerRef = useRef<number | null>(null);

  const startRef = useRef(start);
  startRef.current = start;

  useEffect(() => {
    const onRun = () => {
      void startRef.current();
    };
    window.addEventListener("digest-run", onRun);
    return () => {
      window.removeEventListener("digest-run", onRun);
      abortRef.current?.abort();
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    const node = logRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [lines]);

  useEffect(() => {
    if (phase === "running") {
      setElapsed(0);
      timerRef.current = window.setInterval(() => {
        setElapsed((s) => s + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  }, [phase]);

  const copyLog = () => {
    if (!lines.length) return;
    navigator.clipboard.writeText(lines.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const clearLog = () => {
    setLines([]);
    setPhase("idle");
    setElapsed(0);
  };

  async function start() {
    if (runningRef.current) return;
    runningRef.current = true;
    const controller = new AbortController();
    abortRef.current = controller;
    setPhase("running");
    setLines([]);
    let code = 1;
    let sawDone = false;
    let unavailable = false;
    try {
      const response = await fetch("/api/run", { method: "POST", signal: controller.signal });
      if (!response.ok || !response.body) {
        setLines([`The run did not start (HTTP ${response.status}).`]);
        setPhase("error");
        return;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        const next: string[] = [];
        for (const event of events) {
          const data = event
            .split("\n")
            .filter((row) => row.startsWith("data: "))
            .map((row) => row.slice(6))
            .join("\n");
          if (!data) continue;
          let payload: { line?: string; done?: boolean; code?: number; unavailable?: boolean };
          try {
            payload = JSON.parse(data) as { line?: string; done?: boolean; code?: number };
          } catch {
            continue;
          }
          if (payload.line) next.push(payload.line);
          if (payload.unavailable) unavailable = true;
          if (payload.done) {
            sawDone = true;
            code = payload.code ?? 1;
          }
        }
        if (next.length) setLines((current) => [...current, ...next]);
      }
      setPhase(unavailable ? "unavailable" : sawDone && code === 0 ? "done" : "error");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setLines((current) => [...current, "The stream closed before the run finished."]);
      setPhase("error");
    } finally {
      runningRef.current = false;
    }
  }

  return (
    <section id="run" className="run-drawer is-open" aria-labelledby="run-title">
      <div className="run-bar">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.25rem" }}>
            <h2 id="run-title" style={{ margin: 0 }}>Run Discovery Pipeline</h2>
            <span
              className={`pill-status pill-${
                phase === "running"
                  ? "warn"
                  : phase === "done"
                  ? "pass"
                  : phase === "error"
                  ? "fail"
                  : phase === "unavailable"
                  ? "warn"
                  : "pass"
              }`}
            >
              {phase === "running"
                ? `EXECUTING (${elapsed}s)`
                : phase === "done"
                ? "COMPLETED"
                : phase === "error"
                ? "STOPPED"
                : phase === "unavailable"
                ? "UNAVAILABLE"
                : "READY"}
            </span>
          </div>
          <p>Scrapes past 7 days across SerpApi Google Web & News, extracts via Azure OpenAI, outputs to terminal.</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          {lines.length > 0 && phase !== "running" ? (
            <>
              <button type="button" className="text-link" onClick={copyLog}>
                {copied ? "Copied!" : "Copy Log"}
              </button>
              <button type="button" className="text-link" onClick={clearLog}>
                Clear
              </button>
            </>
          ) : null}
          <button
            type="button"
            className="control run-control"
            onClick={() => void start()}
            disabled={phase === "running"}
          >
            <span className="control-label">
              {phase === "running" ? `Running (${elapsed}s)...` : "Start Pipeline"}
            </span>
          </button>
        </div>
      </div>
      <p className="run-status" role="status" aria-live="polite">
        {phase === "running"
          ? `Streaming pipeline execution logs live (${elapsed}s elapsed)...`
          : phase === "done"
          ? "Execution finished successfully with exit code 0."
          : phase === "error"
          ? "Pipeline halted with an exit error."
          : phase === "unavailable"
          ? "The hosted site cannot run Python directly. Use GitHub Actions or the repository CLI to start a worker run."
          : "Ready to launch discovery sequence."}
      </p>
      {phase === "unavailable" ? (
        <div className="run-bridge" role="note">
          <div>
            <strong>Hosted preview mode</strong>
            <p>
              This page is the judge-facing control room. Vercel serves the interface and live
              diagnostics; the long-running Python worker runs in GitHub Actions or from the
              repository.
            </p>
          </div>
          <div className="run-bridge-actions">
            <a className="control" href="#output">
              Preview digest output
            </a>
            <a className="text-link" href={GITHUB_ACTIONS_HREF} target="_blank" rel="noreferrer">
              Run worker in GitHub Actions ↗
            </a>
            <a className="text-link" href="/guide">
              Open judge guide
            </a>
          </div>
        </div>
      ) : null}
      <pre ref={logRef} className="run-log">
        {lines.length === 0 ? (
          <span className="run-quiet">
            {phase === "unavailable"
              ? "No hosted worker is attached. Use the preview or launch the GitHub Actions worker."
              : 'Click "Start Pipeline" to trigger discovery run.'}
          </span>
        ) : lines.join("\n")}
        {phase === "running" ? <span className="run-caret"> ▍</span> : null}
      </pre>
    </section>
  );
}
