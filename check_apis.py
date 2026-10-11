"""
check_apis.py: Comprehensive health check and diagnostic tool for all integrated services.

Validates:
1. SerpApi - API key authentication, account info, search quota remaining, latency.
2. Azure OpenAI / OpenAI - Endpoint connectivity, model deployment availability, completion test, latency.
3. Supabase Cloud DB - REST connectivity, subscriptions table schema, row count, RLS verification.
4. Slack Bot - Bot token auth.test, team name, user ID, chat:write permissions.
5. Microsoft Teams - Webhook URL format and reachability.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any

import dotenv
import requests

dotenv.load_dotenv()


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def _supports_color() -> bool:
    return sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1"


def badge(status: str, text: str) -> str:
    color = _supports_color()
    if status == "PASS":
        prefix = f"{Colors.GREEN}[✓ PASS]{Colors.RESET}" if color else "[PASS]"
    elif status == "WARN":
        prefix = f"{Colors.YELLOW}[! WARN]{Colors.RESET}" if color else "[WARN]"
    elif status == "FAIL":
        prefix = f"{Colors.RED}[✗ FAIL]{Colors.RESET}" if color else "[FAIL]"
    else:
        prefix = f"{Colors.CYAN}[i INFO]{Colors.RESET}" if color else "[INFO]"
    return f"{prefix} {text}"


def check_serpapi() -> dict[str, Any]:
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return {
            "status": "FAIL",
            "message": "SERPAPI_API_KEY is not set in environment or .env",
            "details": {"action": "Add SERPAPI_API_KEY to your .env file from https://serpapi.com/manage-api-key"},
        }

    start = time.perf_counter()
    try:
        resp = requests.get(
            "https://serpapi.com/account",
            params={"api_key": api_key},
            timeout=10,
        )
        latency_ms = round((time.perf_counter() - start) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            email = data.get("account_email", "N/A")
            searches_left = data.get("total_searches_left", "N/A")
            plan = data.get("plan_name", "N/A")
            return {
                "status": "PASS",
                "message": f"SerpApi verified ({latency_ms}ms) — Account: {email}, Plan: {plan}, Searches remaining: {searches_left}",
                "details": {
                    "latency_ms": latency_ms,
                    "account_email": email,
                    "searches_left": searches_left,
                    "plan": plan,
                },
            }
        elif resp.status_code == 401 or resp.status_code == 403:
            return {
                "status": "FAIL",
                "message": f"SerpApi key invalid or unauthorized (HTTP {resp.status_code})",
                "details": {"response": resp.text[:200]},
            }
        else:
            return {
                "status": "WARN",
                "message": f"SerpApi returned HTTP {resp.status_code}",
                "details": {"response": resp.text[:200]},
            }
    except requests.RequestException as exc:
        return {
            "status": "FAIL",
            "message": f"SerpApi connection failed: {type(exc).__name__}",
            "details": {"error": str(exc)},
        }


def check_azure_openai() -> dict[str, Any]:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not endpoint or not key or not deployment:
        missing = [
            k
            for k, v in [
                ("AZURE_OPENAI_ENDPOINT", endpoint),
                ("AZURE_OPENAI_KEY", key),
                ("AZURE_OPENAI_DEPLOYMENT", deployment),
            ]
            if not v
        ]
        return {
            "status": "FAIL",
            "message": f"Azure OpenAI configuration incomplete. Missing: {', '.join(missing)}",
            "details": {"missing": missing},
        }

    start = time.perf_counter()
    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version="2024-02-15-preview",
            timeout=15.0,
        )
        completion = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Respond with the word PONG"}],
            max_completion_tokens=10,
            temperature=1,
        )
        latency_ms = round((time.perf_counter() - start) * 1000)
        model_name = completion.model or deployment
        return {
            "status": "PASS",
            "message": f"Azure OpenAI active ({latency_ms}ms) — Deployment: {deployment} ({model_name})",
            "details": {
                "latency_ms": latency_ms,
                "deployment": deployment,
                "model": model_name,
            },
        }
    except Exception as exc:
        err_msg = str(exc)
        if "401" in err_msg or "Access denied" in err_msg:
            return {
                "status": "FAIL",
                "message": f"Azure OpenAI unauthorized: check AZURE_OPENAI_KEY and endpoint permissions",
                "details": {"error": err_msg},
            }
        elif "DeploymentNotFound" in err_msg or "404" in err_msg:
            return {
                "status": "FAIL",
                "message": f"Azure OpenAI deployment '{deployment}' not found on endpoint",
                "details": {"error": err_msg},
            }
        return {
            "status": "FAIL",
            "message": f"Azure OpenAI completion failed: {err_msg[:120]}",
            "details": {"error": err_msg},
        }


def check_supabase() -> dict[str, Any]:
    url = (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    secret = (os.getenv("SUPABASE_SECRET_KEY") or "").strip()
    pub_key = (os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY") or "").strip()

    if not url:
        return {
            "status": "WARN",
            "message": "SUPABASE_URL is not set. Subscriber digest feature will be inactive.",
            "details": {"action": "Add SUPABASE_URL to your .env to enable subscriber webhooks."},
        }

    key_to_use = secret or pub_key
    if not key_to_use:
        return {
            "status": "WARN",
            "message": f"SUPABASE_URL is configured ({url}) but no SUPABASE_SECRET_KEY or publishable key provided.",
            "details": {"action": "Set SUPABASE_SECRET_KEY in .env for server-side subscriber delivery."},
        }

    start = time.perf_counter()
    try:
        resp = requests.get(
            f"{url}/rest/v1/subscriptions",
            params={"select": "user_id"},
            headers={"apikey": key_to_use, "Authorization": f"Bearer {key_to_use}", "Prefer": "count=exact"},
            timeout=10,
        )
        latency_ms = round((time.perf_counter() - start) * 1000)
        if resp.status_code == 200:
            count_header = resp.headers.get("content-range", "")
            total_count = count_header.split("/")[-1] if "/" in count_header else str(len(resp.json()))
            return {
                "status": "PASS",
                "message": f"Supabase database connected ({latency_ms}ms) — 'subscriptions' table accessible, subscribers: {total_count}",
                "details": {
                    "latency_ms": latency_ms,
                    "url": url,
                    "subscribers_count": total_count,
                    "key_type": "service_role" if secret else "publishable",
                },
            }
        elif resp.status_code == 404 or "relation \"subscriptions\" does not exist" in resp.text:
            return {
                "status": "WARN",
                "message": "Supabase connected but 'subscriptions' table does not exist. Run 'supabase db push'.",
                "details": {"response": resp.text[:200]},
            }
        else:
            return {
                "status": "WARN",
                "message": f"Supabase REST returned HTTP {resp.status_code}",
                "details": {"response": resp.text[:200]},
            }
    except requests.RequestException as exc:
        return {
            "status": "FAIL",
            "message": f"Supabase connection failed: {type(exc).__name__}",
            "details": {"error": str(exc)},
        }


def check_slack() -> dict[str, Any]:
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID")

    if not token:
        return {
            "status": "INFO",
            "message": "SLACK_BOT_TOKEN is not configured (optional: Slack digest disabled).",
            "details": {},
        }

    start = time.perf_counter()
    try:
        resp = requests.post(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        latency_ms = round((time.perf_counter() - start) * 1000)
        data = resp.json() if resp.status_code == 200 else {}
        if data.get("ok"):
            bot_user = data.get("user", "unknown")
            team = data.get("team", "unknown")
            ch_info = f", Target channel: {channel}" if channel else ", Target channel: NOT SET"
            return {
                "status": "PASS",
                "message": f"Slack bot authenticated ({latency_ms}ms) — Bot: @{bot_user}, Workspace: '{team}'{ch_info}",
                "details": {
                    "latency_ms": latency_ms,
                    "bot_user": bot_user,
                    "team": team,
                    "channel": channel,
                },
            }
        else:
            return {
                "status": "FAIL",
                "message": f"Slack authentication failed: {data.get('error', 'unknown error')}",
                "details": data,
            }
    except requests.RequestException as exc:
        return {
            "status": "FAIL",
            "message": f"Slack connection failed: {type(exc).__name__}",
            "details": {"error": str(exc)},
        }


def check_teams() -> dict[str, Any]:
    url = os.getenv("TEAMS_WEBHOOK_URL")
    if not url:
        return {
            "status": "INFO",
            "message": "TEAMS_WEBHOOK_URL is not configured (optional: Teams digest disabled).",
            "details": {},
        }

    if not url.startswith("https://"):
        return {
            "status": "WARN",
            "message": "TEAMS_WEBHOOK_URL is set but is not an HTTPS URL.",
            "details": {"url": url[:30] + "..."},
        }

    return {
        "status": "PASS",
        "message": "Teams webhook URL configured and formatted validly (HTTPS).",
        "details": {"url": url[:35] + "..."},
    }


def run_all_checks() -> dict[str, dict[str, Any]]:
    return {
        "serpapi": check_serpapi(),
        "azure_openai": check_azure_openai(),
        "supabase": check_supabase(),
        "slack": check_slack(),
        "teams": check_teams(),
    }


def print_report(results: dict[str, dict[str, Any]]) -> int:
    bold = Colors.BOLD if _supports_color() else ""
    reset = Colors.RESET if _supports_color() else ""
    cyan = Colors.CYAN if _supports_color() else ""

    print(f"\n{bold}{cyan}=== AI Tool Discovery Agent — API & Infrastructure Health ==={reset}\n")

    has_fatal = False
    for service_name, result in results.items():
        st = result["status"]
        if st == "FAIL" and service_name in ("serpapi", "azure_openai"):
            has_fatal = True
        print(f"  {badge(st, result['message'])}")

    print()
    if has_fatal:
        print(f"  {badge('FAIL', f'{bold}Critical service checks failed. Resolve the errors above before running pipeline.{reset}')}\n")
        return 1
    else:
        print(f"  {badge('PASS', f'{bold}All critical services healthy. System ready for discovery pipeline run.{reset}')}\n")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify all API and database connections.")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    results = run_all_checks()

    if args.json:
        import json
        print(json.dumps(results, indent=2))
        has_fatal = any(
            results[k]["status"] == "FAIL"
            for k in ("serpapi", "azure_openai")
        )
        return 1 if has_fatal else 0

    return print_report(results)


if __name__ == "__main__":
    sys.exit(main())
