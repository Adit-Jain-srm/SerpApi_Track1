"use client";

import { useEffect } from "react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Runtime error caught:", error);
  }, [error]);

  return (
    <main className="guide" style={{ minHeight: "80vh", display: "flex", flexDirection: "column", justifyContent: "center" }}>
      <div className="subscribe-card" style={{ maxWidth: "34rem" }}>
        <div className="subscribe-badge" style={{ background: "rgba(239, 68, 68, 0.1)", color: "#ef4444", borderColor: "rgba(239, 68, 68, 0.3)" }}>
          <span className="status-dot is-fail" />
          <span>Application Exception</span>
        </div>
        <h1 style={{ fontSize: "2rem", margin: "0.5rem 0" }}>Something unexpected occurred</h1>
        <p style={{ color: "var(--ink-soft)", lineHeight: 1.5 }}>
          The page encountered an error during rendering:
        </p>
        <pre style={{ margin: "1rem 0", padding: "0.75rem", background: "rgba(0,0,0,0.4)", borderRadius: "6px", fontSize: "0.85rem", overflowX: "auto" }}>
          {error.message || "An unknown error was encountered."}
        </pre>
        <div className="actions" style={{ marginTop: "1.25rem" }}>
          <button className="control" onClick={() => reset()}>
            Attempt Recovery
          </button>
          <a className="control control-alt" href="/">
            Return to Discovery Stage
          </a>
        </div>
      </div>
    </main>
  );
}
