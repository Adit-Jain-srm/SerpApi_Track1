"use client";

import { useEffect, useRef, useState } from "react";

interface ServiceReport {
  status: "pass" | "warn" | "fail";
  latencyMs?: number;
  message: string;
  subscribers?: number;
  searchesLeft?: number;
}

interface DiagnosticsData {
  status: "operational" | "degraded";
  uptimeSeconds: number;
  responseTimeMs: number;
  timestamp: string;
  services: {
    supabase: ServiceReport;
    serpapi: ServiceReport;
    pipeline: ServiceReport;
  };
}

export function DiagnosticsDrawer({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [data, setData] = useState<DiagnosticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Webhook Tester state
  const [testUrl, setTestUrl] = useState("");
  const [testingWebhook, setTestingWebhook] = useState(false);
  const [webhookFeedback, setWebhookFeedback] = useState<{
    ok: boolean;
    message: string;
  } | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const fetchDiagnostics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/diagnostics");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load diagnostics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDiagnostics();
    }
  }, [isOpen]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen || !panelRef.current) return;
    const panel = panelRef.current;
    const focusable = () =>
      Array.from(panel.querySelectorAll<HTMLElement>(
        'button, input, textarea, select, [href], [tabindex]:not([tabindex="-1"])',
      )).filter((element) => !element.hasAttribute("disabled"));
    focusable()[0]?.focus();
    const onTab = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const elements = focusable();
      if (!elements.length) return;
      const index = elements.indexOf(document.activeElement as HTMLElement);
      const next = event.shiftKey
        ? index <= 0 ? elements[elements.length - 1] : elements[index - 1]
        : index === elements.length - 1 ? elements[0] : elements[index + 1];
      event.preventDefault();
      next.focus();
    };
    panel.addEventListener("keydown", onTab);
    return () => panel.removeEventListener("keydown", onTab);
  }, [isOpen]);

  const handleTestWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testUrl.trim()) return;
    setTestingWebhook(true);
    setWebhookFeedback(null);
    try {
      const res = await fetch("/api/diagnostics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: testUrl }),
      });
      const result = await res.json();
      if (result.ok) {
        setWebhookFeedback({ ok: true, message: result.message || "Ping delivered successfully!" });
      } else {
        setWebhookFeedback({ ok: false, message: result.error || "Failed to deliver ping" });
      }
    } catch (err: unknown) {
      setWebhookFeedback({
        ok: false,
        message: err instanceof Error ? err.message : "Network error during ping",
      });
    } finally {
      setTestingWebhook(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="diag-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="diag-title">
      <div ref={panelRef} className="diag-panel" onClick={(e) => e.stopPropagation()}>
        <div className="diag-header">
          <div>
            <div className="diag-badge-row">
              <span className={`status-dot ${data?.status === "operational" ? "is-live" : "is-warn"}`} />
              <h2 id="diag-title">System & API Diagnostics</h2>
            </div>
            <p className="diag-subtitle">
              Live connectivity verification across SerpApi, Azure OpenAI, Supabase, and Webhooks.
            </p>
          </div>
          <button className="diag-close" onClick={onClose} aria-label="Close diagnostics">
            ✕
          </button>
        </div>

        <div className="diag-body">
          {loading && !data ? (
            <div className="diag-loading">
              <span className="spinner" />
              <p>Probing live endpoints...</p>
            </div>
          ) : null}

          {error ? (
            <div className="diag-alert is-fail">
              <p>{error}</p>
              <button className="control btn-sm" onClick={fetchDiagnostics}>Retry</button>
            </div>
          ) : null}

          {data ? (
            <div className="diag-grid">
              {/* SerpApi Card */}
              <div className="diag-card">
                <div className="diag-card-top">
                  <span className="diag-card-name">SerpApi Engine</span>
                  <span className={`pill-status pill-${data.services.serpapi.status}`}>
                    {data.services.serpapi.status === "pass" ? "ACTIVE" : data.services.serpapi.status.toUpperCase()}
                  </span>
                </div>
                <p className="diag-card-msg">{data.services.serpapi.message}</p>
                <div className="diag-metrics">
                  <div className="diag-metric">
                    <span className="metric-label">Latency</span>
                    <span className="metric-val">{data.services.serpapi.latencyMs}ms</span>
                  </div>
                  <div className="diag-metric">
                    <span className="metric-label">Quota Left</span>
                    <span className="metric-val">{data.services.serpapi.searchesLeft ?? "—"}</span>
                  </div>
                </div>
              </div>

              {/* Supabase Card */}
              <div className="diag-card">
                <div className="diag-card-top">
                  <span className="diag-card-name">Supabase Cloud DB</span>
                  <span className={`pill-status pill-${data.services.supabase.status}`}>
                    {data.services.supabase.status === "pass" ? "CONNECTED" : data.services.supabase.status.toUpperCase()}
                  </span>
                </div>
                <p className="diag-card-msg">{data.services.supabase.message}</p>
                <div className="diag-metrics">
                  <div className="diag-metric">
                    <span className="metric-label">Latency</span>
                    <span className="metric-val">{data.services.supabase.latencyMs}ms</span>
                  </div>
                  <div className="diag-metric">
                    <span className="metric-label">Subscribers</span>
                    <span className="metric-val">{data.services.supabase.subscribers ?? 0}</span>
                  </div>
                </div>
              </div>

              {/* Azure OpenAI Card */}
              <div className="diag-card">
                <div className="diag-card-top">
                  <span className="diag-card-name">Azure OpenAI Extraction</span>
                  <span className="pill-status pill-warn">CONFIGURED</span>
                </div>
                <p className="diag-card-msg">
                  Azure OpenAI is configured through the Python runner. Run the pipeline for a live extraction probe.
                </p>
                <div className="diag-metrics">
                  <div className="diag-metric">
                    <span className="metric-label">API Model</span>
                    <span className="metric-val">gpt-5.3-chat</span>
                  </div>
                  <div className="diag-metric">
                    <span className="metric-label">Schema</span>
                    <span className="metric-val">ToolInfo v1</span>
                  </div>
                </div>
              </div>

              {/* Python Pipeline Runner */}
              <div className="diag-card">
                <div className="diag-card-top">
                  <span className="diag-card-name">Discovery Pipeline Runner</span>
                  <span className={`pill-status pill-${data.services.pipeline.status}`}>
                    {data.services.pipeline.status === "pass" ? "READY" : "UNAVAILABLE"}
                  </span>
                </div>
                <p className="diag-card-msg">{data.services.pipeline.message}</p>
                <div className="diag-metrics">
                  <div className="diag-metric">
                    <span className="metric-label">Mode</span>
                    <span className="metric-val">Node-Python SSE</span>
                  </div>
                  <div className="diag-metric">
                    <span className="metric-label">Response Time</span>
                    <span className="metric-val">{data.responseTimeMs}ms</span>
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {/* Webhook Tester Section */}
          <div className="diag-tester">
            <h3>Test Incoming Webhook</h3>
            <p className="tester-hint">
              Paste your Slack or Microsoft Teams incoming webhook URL to verify live message delivery.
            </p>
            <form onSubmit={handleTestWebhook} className="tester-form">
              <input
                type="url"
                value={testUrl}
                onChange={(e) => setTestUrl(e.target.value)}
                placeholder="https://hooks.slack.com/... or https://outlook.office.com/..."
                required
                className="tester-input"
              />
              <button type="submit" className="control" disabled={testingWebhook}>
                {testingWebhook ? "Sending Ping..." : "Send Test Ping"}
              </button>
            </form>

            {webhookFeedback ? (
              <div className={`diag-feedback ${webhookFeedback.ok ? "is-ok" : "is-err"}`}>
                <span>{webhookFeedback.ok ? "✓" : "✗"}</span>
                <p>{webhookFeedback.message}</p>
              </div>
            ) : null}
          </div>
        </div>

        <div className="diag-footer">
          <button className="text-link" onClick={fetchDiagnostics} disabled={loading}>
            {loading ? "Checking..." : "↻ Refresh Diagnostics"}
          </button>
          <button className="control" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
