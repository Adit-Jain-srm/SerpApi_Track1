# Keys

The digest needs a SerpApi key and an Azure OpenAI deployment. Microsoft Teams and Slack are optional. Slack sits beside Teams. The public site takes one Vercel variable.

Copy `.env.example` to `.env` in the repo root and fill it in there. `.env` is gitignored. Do not commit a filled env file, and do not paste a key into a URL.

| Variable | Required | Where it is used |
|---|---|---|
| `SERPAPI_API_KEY` | Yes | Local pipeline, and the one Vercel variable |
| `AZURE_OPENAI_ENDPOINT` | Yes | Page extraction |
| `AZURE_OPENAI_KEY` | Yes | Page extraction |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Page extraction |
| `TEAMS_WEBHOOK_URL` | No | Teams delivery |
| `SLACK_BOT_TOKEN` | No | Slack digest posts |
| `SLACK_CHANNEL_ID` | No | Slack channel that receives the digest |
| `SLACK_APP_TOKEN` | No | Stored for a future socket-mode listener; not used to post |
| `BATCH_SIZE` | No | Concurrent page fetches |
| `LLM_CONCURRENCY_LIMIT` | No | Concurrent Azure calls |
| `SEARCH_DAYS` | No | Default date window when `--days` is omitted |

`serpapi-search-tools` also accepts `SERPAPI_KEY`. This repo's docs and `.env.example` use `SERPAPI_API_KEY` only. Serper is not used. Do not add `SERPER_API_KEY`.

## SerpApi

Create a key in the SerpApi dashboard: [serpapi.com/manage-api-key](https://serpapi.com/manage-api-key). Put it in `SERPAPI_API_KEY`.

Each run issues eight searches: four launch-intent queries, once through web search and once through news search. That cap exists because the free plan draws from a monthly credit pool. Eight searches is a digest of recent launches. It is not a crawl. Raising the query count spends that pool on every run.

A missing `SERPAPI_API_KEY` is a configuration error. The process exits before it searches.

## Azure OpenAI

Extraction calls your Azure OpenAI deployment. Set all three:

- `AZURE_OPENAI_ENDPOINT` — resource URL, including the trailing slash, such as `https://your-resource.openai.azure.com/`
- `AZURE_OPENAI_KEY` — key for that resource
- `AZURE_OPENAI_DEPLOYMENT` — deployment name

A missing endpoint or key is a configuration error, including on `--dry-run`. Dry-run does not call Azure. A full extraction also needs `AZURE_OPENAI_DEPLOYMENT`.

## Teams

`TEAMS_WEBHOOK_URL` is an incoming webhook for the channel that should receive the digest. Leave it empty to print the console summary only. `--skip-teams` skips the webhook even when the variable is set, and still prints the console summary.

## Slack

Slack is optional and sits beside Teams. The digest is posted with `chat.postMessage`. This pipeline does not open a Socket Mode connection.

The Slack app is **AI-Search-Buddy**. Posting needs the bot token and the channel ID:

- `SLACK_BOT_TOKEN` — bot token for that app
- `SLACK_CHANNEL_ID` — ID of the channel that should receive the digest

`SLACK_APP_TOKEN` is stored for a future socket-mode listener. This pipeline does not read it when posting.

Leave the bot token or the channel ID empty to skip Slack. The run logs a warning and continues, including any Teams posts. `--skip-slack` skips Slack even when both values are set. `--dry-run` does not post to Slack or to Teams.

A Slack API error for one tool is logged. The rest of the run continues.

The bot must be invited to the channel. Copy the channel ID, not the channel name:

1. In Slack, invite **AI-Search-Buddy** to the channel.
2. Open the channel and click its name to open the details.
3. On the About tab, copy the Channel ID at the bottom. Public channel IDs start with `C`. Private channel IDs start with `G`.
4. Paste that ID into `SLACK_CHANNEL_ID`.

A name such as `#launches` will not work.

## Vercel

The public page deploys with project root `web/`. Set one variable on that project:

- `SERPAPI_API_KEY`

Do not add the Azure endpoint, the Azure key, the deployment name, the Teams webhook, or the Slack tokens to Vercel. The live proof route calls SerpApi with the fixed digest query and the same date window. If `SERPAPI_API_KEY` is unset there, the page stays on its sample cards.
