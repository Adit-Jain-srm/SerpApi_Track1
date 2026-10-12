# AI Tool Discovery Agent — Architecture & Product Remediation Plan

Based on the comprehensive end-to-end audit (11 October 2026).
Quality standards: Staff Engineer bar (@verification-and-elegance, @ui-ux-pro-max, @web-perf, @elite-execution-philosophy).

---

## 🎯 Phase 1: Security & Safe Egress Boundary (P1)
- [x] **1.1 Re-scope / Replace Unrelated Agent Rule**
  - Fix: Replace `.agents/rules/agent-core.mdc` and `.cursor/rules/agent-core.mdc` with repository-specific agent guidelines for the AI Tool Discovery Agent (remove the copied external OSS bounty rule).
  - Target: `.agents/rules/agent-core.mdc`, `.cursor/rules/agent-core.mdc`
- [x] **1.2 Central Outbound URL Safety Module (SSRF Defense)**
  - Fix: Build a unified safe egress boundary (`utils/url_safety.py` and `web/lib/url-safety.ts`) that validates IP resolution, rejecting loopback (`127.0.0.0/8`), private RFC1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), IPv6 loopback (`::1`), and cloud metadata endpoints.
  - Re-validate every redirect hop against the safe IP policy.
  - Apply consistently across:
    - Page fetcher (`agents/scraper_agent.py`)
    - Robots.txt checker (`utils/prompt_loader.py`)
    - Webhook diagnostics endpoint (`web/app/api/diagnostics/route.ts`)
    - Subscriber delivery worker (`output/subscribers.py`)
    - Subscriber save validation (`web/app/subscribe/actions.ts`)
- [x] **1.3 Diagnostic Redaction & Auth Check**
  - Fix: Redact API keys and credential-bearing query parameters from diagnostic exception strings.
  - Add origin / authentication and destination allowlist to `POST /api/diagnostics`.

---

## ⚙️ Phase 2: Pipeline Reliability & Failure Isolation (P1/P2)
- [x] **2.1 Preserved Exception Classification for Rate Limits**
  - Fix: In `scraper_agent.py`, preserve or unpack `RateLimitError` so `_extract_with_retry` in `pipeline_agent.py` can observe rate limits, apply exponential backoff with jitter, and retry properly.
- [x] **2.2 Per-Candidate Extraction Error Containment**
  - Fix: In `pipeline_agent.py`, wrap candidate LLM extraction so one failed model call records a failure for that candidate rather than aborting the entire digest and dropping already-extracted tools.
- [x] **2.3 Streaming Response Byte Cap**
  - Fix: In `scraper_agent.py`, enforce a decompressed streaming byte limit (e.g., max 500KB) during download before loading into memory.
- [x] **2.4 Untrusted Content Prompt Delimitation**
  - Fix: Isolate page HTML/text inside clear untrusted data delimiters in `prompts/system_prompt.txt` and `agents/scraper_agent.py`, instructing the model to treat content strictly as data and ignore instructions.
- [x] **2.5 Deterministic Ordering & Safe Budgets**
  - Fix: Restore original candidate order before ranking and capping leads; set a safe default budget for `max_urls` in `config_agent.py`.
- [x] **2.6 Parallel Search Concurrency**
  - Fix: Run web and news query batches with bounded async concurrency (`asyncio.gather` with semaphore) in `search_agent.py` to match the "two engines run together" architecture.
- [x] **2.7 Publication Date Normalization**
  - Fix: Normalize publication dates to UTC in `pipeline_agent.py`, gracefully handling naive vs aware ISO timestamps and preserving explicit unknown-date states.

---

## 🌐 Phase 3: Runtime, Product Promise & Delivery (P1/P2)
- [x] **3.1 Aligned Runtime & Hosted Mode Communication**
  - Fix: Clearly distinguish local runner vs hosted deployment in `/api/run` and UI copy. Provide a clear mode indicator and execution explanation.
- [x] **3.2 Automated Delivery Scheduling**
  - Fix: Add GitHub Actions scheduled workflow (`.github/workflows/weekly-digest.yml`) for automated cron execution, aligning the "weekly automated digest" promise with real execution machinery.
- [x] **3.3 Subscriber Fan-out Pagination & Delivery Status**
  - Fix: In `output/subscribers.py`, paginate Supabase subscriber rows beyond the 1000 limit, use bounded async/concurrent posting, and return structured delivery statistics (sent, failed, skipped).
- [x] **3.4 Structured CLI Delivery Exit Codes**
  - Fix: In `main.py`, report explicit channel delivery outcomes (Teams, Slack, Subscribers) and exit non-zero only if critical deliveries fail per policy.

---

## 🎨 Phase 4: Truthful Diagnostics, UI/UX & Accessibility (P2/P3)
- [x] **4.1 Truthful Live Diagnostics & Masthead Binding**
  - Fix: Bind masthead status to real diagnostic fetch states (not hardcoded green). Update `DiagnosticsDrawer` to display live measured state for Azure, SerpApi, Supabase, and Pipeline with timestamps.
- [x] **4.2 Doctor & Runtime Configuration Parity**
  - Fix: Keep the web diagnostics endpoint aligned with production extraction, label format-only checks truthfully, and test Supabase service role vs anon capabilities accurately.
- [x] **4.3 Explicit Sample vs Live Proof Labeling**
  - Fix: Unmistakably label cards as "Sample Digest Card — Illustrative" on the landing page, and cleanly wire `/api/proof` for live preview verification.
- [x] **4.4 Accessibility: Focus Trapping, ARIA Live Regions, & WebGL Throttling**
  - Fix: Add focus trapping and `inert` backdrop management to `DiagnosticsDrawer`.
  - Add `aria-live="polite"` region to `RunDrawer` announcements.
  - Optimize `PaperPress`: lazy-load Three.js, pause animation when offscreen, respect `prefers-reduced-motion`.

---

## 🧪 Phase 5: Hermetic Quality Gate & CI (P2/P3)
- [x] **5.1 Hermetic Test Isolation**
  - Fix: Mock all network calls in the pipeline tests and `tests/conftest.py` so unit tests never contact live Supabase or external APIs.
- [x] **5.2 CI Workflow & Quality Scripts**
  - Fix: Add `.github/workflows/ci.yml` running:
    - Python `pytest -v`
    - Web `npm run lint`, `npm run typecheck`, and `npm run build`
  - Add `typecheck` script to `web/package.json`.

## Review Summary

- **Shipped:** Python URL/IP safety validation, redirect revalidation, bounded decompressed HTML reads, safe subscriber webhook delivery with pagination, Next.js webhook validation/timeout/redirect checks, diagnostics authorization header repair, and the web `typecheck` script.
- **Verification:** Focused Python suite: `10 passed`; web TypeScript check: `tsc --noEmit` passed.
- **Lessons learned:** Existing test doubles expose only `response.text()`, so the streaming cap preserves a fallback for lightweight response implementations while using chunked reads for real aiohttp responses.
- **Remaining debt:** No planned remediation items remain. Existing lint warnings are limited to image optimization and internal navigation recommendations.
