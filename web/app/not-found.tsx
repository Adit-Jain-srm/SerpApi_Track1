import Link from "next/link";

export default function NotFound() {
  return (
    <main className="guide" style={{ minHeight: "80vh", display: "flex", flexDirection: "column", justifyContent: "center" }}>
      <div className="subscribe-card" style={{ maxWidth: "34rem" }}>
        <div className="subscribe-badge" style={{ background: "rgba(245, 158, 11, 0.1)", color: "#f59e0b", borderColor: "rgba(245, 158, 11, 0.3)" }}>
          <span className="status-dot is-warn" />
          <span>404 Not Found</span>
        </div>
        <h1 style={{ fontSize: "2rem", margin: "0.5rem 0" }}>Page Does Not Exist</h1>
        <p style={{ color: "var(--ink-soft)", lineHeight: 1.5 }}>
          The requested route was not found in the AI Tool Discovery Agent console.
        </p>
        <div className="actions" style={{ marginTop: "1.25rem" }}>
          <Link className="control" href="/">
            ← Return to Discovery Stage
          </Link>
          <Link className="text-link" href="/guide">
            Read Documentation
          </Link>
        </div>
      </div>
    </main>
  );
}
