"use server";

import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";
import { validateWebhookUrl } from "@/lib/url-safety";

async function httpsWebhook(value: FormDataEntryValue | null): Promise<string | null> {
  if (typeof value !== "string") return null;
  const text = value.trim();
  if (!text) return null;
  try {
    return (await validateWebhookUrl(text)).toString();
  } catch {
    return null;
  }
}

export async function signIn(formData: FormData) {
  const email = String(formData.get("email") || "").trim();
  const password = String(formData.get("password") || "");
  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) redirect(`/subscribe?error=${encodeURIComponent(error.message)}`);
  redirect("/subscribe");
}

export async function signUp(formData: FormData) {
  const email = String(formData.get("email") || "").trim();
  const password = String(formData.get("password") || "");
  const supabase = await createClient();
  const { error } = await supabase.auth.signUp({ email, password });
  if (error) redirect(`/subscribe?error=${encodeURIComponent(error.message)}`);
  redirect("/subscribe?notice=Check your email if confirmation is required, or save your webhooks.");
}

export async function signOut() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/subscribe");
}

export async function saveSubscription(formData: FormData) {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getClaims();
  const userId = data?.claims?.sub;
  if (error || !userId) redirect("/subscribe?error=Sign%20in%20first.");

  const teamsRaw = formData.get("teams");
  const slackRaw = formData.get("slack");
  const teams = await httpsWebhook(teamsRaw);
  const slack = await httpsWebhook(slackRaw);
  const teamsInvalid = typeof teamsRaw === "string" && teamsRaw.trim() && !teams;
  const slackInvalid = typeof slackRaw === "string" && slackRaw.trim() && !slack;
  if (teamsInvalid || slackInvalid) {
    redirect("/subscribe?error=Webhook%20URLs%20must%20be%20https.");
  }

  const { error: writeError } = await supabase.from("subscriptions").upsert({
    user_id: userId,
    teams_webhook_url: teams,
    slack_webhook_url: slack,
    active: Boolean(teams || slack),
    updated_at: new Date().toISOString(),
  });
  if (writeError) redirect("/subscribe?error=Could%20not%20save%20the%20subscription.");
  redirect("/subscribe?notice=Saved.%20A%20digest%20run%20will%20post%20to%20these%20webhooks.");
}
