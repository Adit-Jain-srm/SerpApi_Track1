# SerpApi India Hackathon — Track 01

Track 01 is AI Agents: plan, search, compare, and act on current information. This repo is that agent. Search data is required. Without the SerpApi web and news responses there is no candidate list, and the model is not asked to invent launches.

## Existing project

The project existed before this hackathon. An earlier version searched with Serper and a raw SerpApi client, then scraped pages and extracted them with Azure OpenAI.

This submission keeps the extractor, the blacklist, the prompts, and the console and Teams delivery. Serper is gone. Search is `serpapi-search-tools`: a date plan, `web_search` and `news_search`, then a compare step before any page is fetched. The submitted SerpApi web-and-news path, CLI, tests, Slack output, and public site are part of this submission.

AI tools used on this submission: Cursor.

## Judging map

Judges look at the idea, originality, complexity, usefulness, and whether search data is required. The run is those four steps.

### Plan

`--days` (default 7, or `SEARCH_DAYS` when that variable is set and the flag is omitted) builds one date window.

- Web search is pinned to `google` with `tbs=qdr:d{N}` (seven days is `tbs=qdr:d7`). Web queries do not get an `after:` suffix.
- News search is `google_news`. The cutoff is `after:YYYY-MM-DD` inside the query, using the UTC start of the window. News does not receive `tbs`.

The query set is four launch intents: new tool, new app, now available, and open-source launch. Four queries times two engines is eight searches, which stays inside the free monthly credit pool.

### Search

`web_search` and `news_search` come from `serpapi-search-tools` (`provider="function"`, JSON responses, `hl=en`, `gl=us`). Web links are `organic_results[].link`. News links are `news_results[].link`. A `no_results` payload is an empty list. If one engine fails, the run logs `SerpApiSearchError` and continues with the other. If both fail, the process exits non-zero and does not print an empty digest as success.

### Compare

Comparison happens before any fetch. Each candidate keeps its URL, title, snippet, `published_at`, and which engines produced it. URLs are normalized, aggregator domains are dropped, and duplicates merge. When web and news disagree on the date, the news date is kept. `--max-urls` caps how many candidates continue.

### Act

The scraper fetches the compared URLs over TLS and Azure OpenAI extracts a `ToolInfo`. The console prints the summary. Teams gets a message only when `TEAMS_WEBHOOK_URL` is set and `--skip-teams` was not passed. Slack gets a message only when `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_ID` are set and `--skip-slack` was not passed. A missing webhook, token, or channel skips that output and leaves the console summary.

- `--dry-run` needs `SERPAPI_API_KEY` only. It prints the comparison table and does not fetch, call Azure, or post to Teams or Slack.
- `--days 0`, a negative `--days`, `--max-urls 0`, and a negative `--max-urls` exit with code 2 and a one-line usage error. They do not search.
- If one engine fails, the run continues with the other. If both fail, the process exits non-zero.
- `--skip-teams` and `--skip-slack` still print the console summary.

Usefulness is the short list a team can read: launches inside the window, with aggregators already removed, delivered in the console, in Teams, or in Slack. The live film is [https://serpapi-track1.vercel.app](https://serpapi-track1.vercel.app) and the command guide is [https://serpapi-track1.vercel.app/guide](https://serpapi-track1.vercel.app/guide).

## Local demo (under three minutes)

Record the terminal and this README. No live key on screen. Blur `.env` if it is open. The dry-run is the search proof. The second command is the act proof, capped so Azure stays short.

| Time | On screen | What to say |
|---|---|---|
| 0:00–0:20 | README title and author | "This is a digest of AI tools that launched inside a date window, for a team that cannot watch the open web. The project existed before this hackathon. This submission is Track 01." |
| 0:20–0:40 | `.env.example` and `docs/KEYS.md` | "SerpApi web and news are required. Serper is not used. The key stays in `.env`. A run is eight searches because of the free credit pool." |
| 0:40–1:25 | `python main.py --dry-run --days 7` | "Plan, then search, then compare. Web is Google with `tbs=qdr:d7`. News uses `after:` and the UTC date seven days back. This table is the candidate list. Nothing is fetched." |
| 1:25–2:20 | `python main.py --days 7 --max-urls 3 --skip-teams --skip-slack` | "Compare already chose the URLs. Azure extracts only those pages. Teams and Slack are skipped. The console list is the digest." |
| 2:20–2:40 | Sample Teams message in the README | "With a webhook, each tool is this message. The website line is omitted when it matches the source." |
| 2:40–3:00 | `docs/MCP.md` warning | "The pipeline does not call MCP. Interactive clients use `https://mcp.serpapi.com/mcp` and `Authorization: Bearer` from `SERPAPI_API_KEY`. The key never goes in the URL." |

If the second command would spend credits you want to save, stop after the dry-run and say that fetch and Azure are the next step, then show the sample Teams message. That cut still fits the three minutes. A full Teams post is optional and needs `TEAMS_WEBHOOK_URL`.
