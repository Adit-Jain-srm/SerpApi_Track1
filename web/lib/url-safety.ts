import { lookup } from "node:dns/promises";
import { isIP } from "node:net";

const BLOCKED_HOSTNAMES = new Set(["localhost", "metadata", "metadata.google.internal"]);
const ALLOWED_WEBHOOK_HOSTS = new Set(["hooks.slack.com", "outlook.office.com"]);

function blockedAddress(address: string): boolean {
  const normalized = address.toLowerCase();
  if (normalized === "::1" || normalized.startsWith("127.")) return true;
  if (normalized.startsWith("10.") || normalized.startsWith("192.168.")) return true;
  if (/^172\.(1[6-9]|2\d|3[01])\./.test(normalized)) return true;
  if (normalized.startsWith("169.254.")) return true;
  if (normalized === "0.0.0.0" || normalized.startsWith("fc") || normalized.startsWith("fd")) return true;
  if (normalized.startsWith("fe80:")) return true;
  return false;
}

function allowedWebhookHost(hostname: string): boolean {
  return (
    ALLOWED_WEBHOOK_HOSTS.has(hostname) ||
    hostname.endsWith(".webhook.office.com") ||
    hostname.endsWith(".logic.azure.com")
  );
}

export async function validateWebhookUrl(value: string): Promise<URL> {
  let url: URL;
  try {
    url = new URL(value.trim());
  } catch {
    throw new Error("A valid HTTPS webhook URL is required.");
  }
  const hostname = url.hostname.toLowerCase().replace(/\.$/, "");
  if (url.protocol !== "https:" || !allowedWebhookHost(hostname) || BLOCKED_HOSTNAMES.has(hostname)) {
    throw new Error("Webhook host is not an approved Teams or Slack endpoint.");
  }

  if (!isIP(hostname)) {
    const addresses = await lookup(hostname, { all: true, verbatim: true });
    if (!addresses.length || addresses.some(({ address }) => blockedAddress(address))) {
      throw new Error("Webhook host resolves to a blocked address.");
    }
  } else if (blockedAddress(hostname)) {
    throw new Error("Webhook host resolves to a blocked address.");
  }
  return url;
}
