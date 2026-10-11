"use client";

import { useState } from "react";

export function WebhookTester({ inputName }: { inputName: string }) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  const testWebhook = async () => {
    const input = document.querySelector<HTMLInputElement>(`input[name="${inputName}"]`);
    const url = input?.value.trim();
    if (!url) {
      setResult({ ok: false, message: "Please paste a webhook URL first." });
      return;
    }
    if (!url.startsWith("https://")) {
      setResult({ ok: false, message: "Webhook URL must start with https://" });
      return;
    }

    setTesting(true);
    setResult(null);
    try {
      const res = await fetch("/api/diagnostics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (data.ok) {
        setResult({ ok: true, message: "✓ Test ping received! Webhook is verified." });
      } else {
        setResult({ ok: false, message: `✗ Error: ${data.error || "Delivery failed"}` });
      }
    } catch (err: unknown) {
      setResult({
        ok: false,
        message: err instanceof Error ? err.message : "Network error during test",
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="webhook-tester-inline">
      <button
        type="button"
        className="control control-xs"
        onClick={testWebhook}
        disabled={testing}
      >
        {testing ? "Pinging..." : "Test Webhook"}
      </button>
      {result ? (
        <span className={`tester-result ${result.ok ? "is-ok" : "is-err"}`}>
          {result.message}
        </span>
      ) : null}
    </div>
  );
}
