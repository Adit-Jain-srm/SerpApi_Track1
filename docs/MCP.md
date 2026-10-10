# SerpApi MCP

The hosted MCP server is an interactive client for Cursor, Claude, and Codex. The digest pipeline does not speak MCP. It calls `web_search` and `news_search` through `serpapi-search-tools`.

Use the hosted server at `https://mcp.serpapi.com/mcp` with a bearer header. The key comes from `SERPAPI_API_KEY` in the environment. SerpApi recommends the header because a key in the URL can show up in logs.

```text
Authorization: Bearer <value of SERPAPI_API_KEY>
```

## Do not put the key in the URL

Do not configure, document, or commit:

```text
https://mcp.serpapi.com/<key>/mcp
```

That path puts the API key in the URL. A committed `mcp.json`, a shell history line, or a log line then contains the secret. Header auth avoids that. If a key was ever committed in that URL, revoke it in the SerpApi dashboard and create a new one.

## Cursor

Remote MCP entries do not load an env file. Export `SERPAPI_API_KEY` in the environment Cursor inherits, then point Cursor at the hosted server. Cursor interpolates `${env:NAME}` in `headers`. Put this in your user MCP config (`~/.cursor/mcp.json`), not in a file that contains the raw key:

```json
{
  "mcpServers": {
    "serpapi": {
      "url": "https://mcp.serpapi.com/mcp",
      "headers": {
        "Authorization": "Bearer ${env:SERPAPI_API_KEY}"
      }
    }
  }
}
```

The value after `Bearer` must stay the `${env:SERPAPI_API_KEY}` reference. Replacing it with the key commits the secret if that JSON is saved into the repo.

## Claude Code

```bash
claude mcp add --transport http serpapi https://mcp.serpapi.com/mcp --header "Authorization: Bearer $SERPAPI_API_KEY"
```

PowerShell:

```powershell
claude mcp add --transport http serpapi https://mcp.serpapi.com/mcp --header "Authorization: Bearer $env:SERPAPI_API_KEY"
```

Pass the header from the environment. Do not write the key into the command you commit or paste into a tracked note.

## Codex

Codex reads the key from `SERPAPI_API_KEY`:

```bash
codex mcp add serpapi --url https://mcp.serpapi.com/mcp --bearer-token-env-var SERPAPI_API_KEY
```

## What the pipeline uses instead

`python main.py` builds its own client with `provider="function"` and never opens `mcp.serpapi.com`. An MCP chat can search ad hoc. The weekly digest cannot, and it will not pick up tools you called from an interactive session.

The digest date window, comparison table, and delivery flags are the CLI in the README, not MCP tools. `--days 0` and `--max-urls 0` exit with code 2 before any search. `--dry-run` still calls SerpApi through this library and stops before page fetch. The public site at `https://serpapi-track1.vercel.app` proves one fixed Google query. Its guide is `/guide`. That site does not run this MCP client.
