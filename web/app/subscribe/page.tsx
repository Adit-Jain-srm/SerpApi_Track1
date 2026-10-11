import type { Metadata } from "next";

import { saveSubscription, signIn, signOut, signUp } from "@/app/subscribe/actions";
import { WebhookTester } from "@/components/webhook-tester";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = {
  title: "Subscribe to Weekly Digest — AI Tool Discovery Agent",
  description: "Sign in and save your Microsoft Teams or Slack incoming webhook to receive weekly AI tool discoveries automatically.",
};

export default async function SubscribePage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; notice?: string }>;
}) {
  const params = await searchParams;
  const configured = Boolean(
    (process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL) &&
    (process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_SECRET_KEY)
  );

  let email = "";
  let teams = "";
  let slack = "";

  if (configured) {
    try {
      const supabase = await createClient();
      const { data: { user } } = await supabase.auth.getUser();
      email = user?.email ?? "";
      const userId = user?.id;
      if (userId) {
        const { data: row } = await supabase
          .from("subscriptions")
          .select("teams_webhook_url, slack_webhook_url")
          .eq("user_id", userId)
          .maybeSingle();
        teams = row?.teams_webhook_url ?? "";
        slack = row?.slack_webhook_url ?? "";
      }
    } catch {
      // Supabase unavailable or unauthenticated
    }
  }

  return (
    <main className="guide subscribe-page">
      <nav className="guide-nav" aria-label="Breadcrumbs">
        <a href="/">← Weekly Digest</a>
        <a href="/guide">Documentation</a>
      </nav>

      <div className="subscribe-header">
        <div className="subscribe-badge">
          <span className="status-dot is-live" />
          <span>Automated Delivery</span>
        </div>
        <h1>Subscribe to the Digest</h1>
        <p className="guide-lead">
          Connect your organization’s Microsoft Teams or Slack workspace. Each pipeline run delivers concise, structured cards detailing newly launched AI products straight to your channels.
        </p>
      </div>

      {params.error ? (
        <div className="subscribe-alert is-error" role="alert">
          <span className="alert-icon">⚠</span>
          <p>{params.error}</p>
        </div>
      ) : null}

      {params.notice ? (
        <div className="subscribe-alert is-notice" role="status">
          <span className="alert-icon">✓</span>
          <p>{params.notice}</p>
        </div>
      ) : null}

      {!configured ? (
        <div className="subscribe-card is-warning">
          <h3>Supabase Storage Inactive</h3>
          <p>
            Supabase environment variables are missing on this deployment. Add <code>NEXT_PUBLIC_SUPABASE_URL</code> and <code>NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY</code> to enable subscription storage.
          </p>
        </div>
      ) : null}

      {configured && !email ? (
        <div className="subscribe-split">
          <div className="subscribe-card">
            <h2>Account Access</h2>
            <p className="card-hint">
              Sign in or create an account to securely store and update your webhook subscriptions.
            </p>
            <form className="subscribe-form" action={signIn}>
              <label>
                <span>Email Address</span>
                <input name="email" type="email" autoComplete="email" placeholder="you@company.com" required />
              </label>
              <label>
                <span>Password</span>
                <input name="password" type="password" autoComplete="current-password" minLength={8} placeholder="••••••••" required />
              </label>
              <div className="actions auth-actions">
                <button className="control" type="submit">
                  Sign in
                </button>
                <button className="control control-alt" type="submit" formAction={signUp}>
                  Create account
                </button>
              </div>
            </form>
          </div>

          <div className="subscribe-info-panel">
            <h3>Enterprise Privacy & Security</h3>
            <ul className="info-list">
              <li>
                <strong>Row-Level Security (RLS)</strong>
                <span>Each user can only read and modify their own webhook record. Webhook endpoints are never shared with other tenants.</span>
              </li>
              <li>
                <strong>Encrypted TLS Only</strong>
                <span>Webhook endpoints must use HTTPS protocols. Non-secure URLs are strictly rejected at the database level.</span>
              </li>
              <li>
                <strong>Zero Secret Leakage</strong>
                <span>Incoming webhooks are dispatched server-side by the worker pipeline and are never exposed in browser network payloads.</span>
              </li>
            </ul>
          </div>
        </div>
      ) : null}

      {configured && email ? (
        <div className="subscribe-split">
          <div className="subscribe-card">
            <div className="account-meta">
              <div>
                <span className="meta-label">Signed in as</span>
                <strong className="meta-value">{email}</strong>
              </div>
              <form action={signOut} className="subscribe-inline">
                <button className="text-link" type="submit">
                  Sign out
                </button>
              </form>
            </div>

            <h2>Configure Delivery Channels</h2>
            <p className="card-hint">
              Paste incoming webhooks for Microsoft Teams, Slack, or both. Use the Test Webhook button to verify ping connectivity.
            </p>

            <form className="subscribe-form" action={saveSubscription}>
              <div className="field-group">
                <label>
                  <span>Microsoft Teams Webhook URL</span>
                  <input
                    name="teams"
                    type="url"
                    inputMode="url"
                    placeholder="https://outlook.office.com/webhook/..."
                    defaultValue={teams}
                  />
                </label>
                <WebhookTester inputName="teams" />
              </div>

              <div className="field-group">
                <label>
                  <span>Slack Incoming Webhook URL</span>
                  <input
                    name="slack"
                    type="url"
                    inputMode="url"
                    placeholder="https://hooks.slack.com/services/..."
                    defaultValue={slack}
                  />
                </label>
                <WebhookTester inputName="slack" />
              </div>

              <div className="actions">
                <button className="control" type="submit">
                  Save Webhook Subscriptions
                </button>
              </div>
            </form>
          </div>

          <div className="subscribe-info-panel">
            <h3>Subscription Status</h3>
            <div className="status-summary">
              <div className="summary-item">
                <span>Teams Status</span>
                <strong>{teams ? "Configured & Active" : "Unset"}</strong>
              </div>
              <div className="summary-item">
                <span>Slack Status</span>
                <strong>{slack ? "Configured & Active" : "Unset"}</strong>
              </div>
              <div className="summary-item">
                <span>Storage</span>
                <strong>Supabase PostgreSQL RLS</strong>
              </div>
            </div>

            <h3 style={{ marginTop: "1.5rem" }}>Testing Guidelines</h3>
            <p style={{ fontSize: "0.95rem", lineHeight: 1.5, color: "var(--ink-soft)" }}>
              After entering your webhook, click <strong>Test Webhook</strong> to immediately verify incoming payloads. When the weekly discovery pipeline executes, all kept tools will be broadcast to your connected channels.
            </p>
          </div>
        </div>
      ) : null}
    </main>
  );
}
