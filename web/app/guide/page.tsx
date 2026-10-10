import type { Metadata } from "next";

const GITHUB_HREF = "https://github.com/Adit-Jain-srm/SerpApi_Track1";

export const metadata: Metadata = {
  title: "Run the digest",
  description:
    "Install the weekly digest, set the required keys, and run it from the command line.",
};

export default function GuidePage() {
  return (
    <main className="guide">
      <p className="guide-nav">
        <a href="/">Digest film</a>
        <a href={GITHUB_HREF} rel="noreferrer">
          SerpApi Track 1 on GitHub
        </a>
      </p>
      <h1>Run the digest</h1>
      <p className="guide-lead">
        Python 3.10 or newer. The tool plans a date window, searches, compares the hits, and prints a digest. Teams and Slack post only when their keys are set.
      </p>

      <figure className="guide-still">
        <img
          src="/teams_output_example.png"
          width={1024}
          height={506}
          alt="Sample Teams digest for Quibim, with title, website, audience, overview, features, pricing, and source."
        />
        <figcaption>
          Sample of the digest shape. Not a claim this tool was found today.
        </figcaption>
      </figure>

      <h2>Install</h2>
      <p>From the repo root, create a virtual environment and install the requirements.</p>
      <pre>
        <code>python -m venv .venv</code>
      </pre>
      <p>Windows PowerShell, after the environment exists:</p>
      <pre>
        <code>{String.raw`.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env`}</code>
      </pre>
      <p>
        If script activation is blocked, open cmd and run <code>.venv\Scripts\activate.bat</code> instead.
      </p>
      <p>Unix:</p>
      <pre>
        <code>{`source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env`}</code>
      </pre>

      <h2>Keys</h2>
      <p>
        Copy <code>.env.example</code> to <code>.env</code> and fill in the names below. Do not commit <code>.env</code>. This page does not contain key values.
      </p>
      <p>Required:</p>
      <ul>
        <li>
          <code>SERPAPI_API_KEY</code>
        </li>
        <li>
          <code>AZURE_OPENAI_ENDPOINT</code>
        </li>
        <li>
          <code>AZURE_OPENAI_KEY</code>
        </li>
        <li>
          <code>AZURE_OPENAI_DEPLOYMENT</code>
        </li>
      </ul>
      <p>Optional:</p>
      <ul>
        <li>
          <code>TEAMS_WEBHOOK_URL</code>. Leave it empty to print the console summary and skip Teams.
        </li>
        <li>
          <code>SLACK_BOT_TOKEN</code> and <code>SLACK_CHANNEL_ID</code>. Leave either empty to skip Slack. Posting needs both.
        </li>
      </ul>
      <p>
        <code>--dry-run</code> still expects the SerpApi and Azure names to be present. It does not call Azure.
      </p>

      <h2>Run</h2>
      <p>From the repo root, with the virtual environment active:</p>
      <pre>
        <code>python main.py</code>
      </pre>

      <h2>Flags</h2>
      <dl className="guide-flags">
        <div>
          <dt>
            <code>--days</code>
          </dt>
          <dd>Date window in days. Default 7, or SEARCH_DAYS when the flag is omitted.</dd>
        </div>
        <div>
          <dt>
            <code>--dry-run</code>
          </dt>
          <dd>Print the comparison table. Do not fetch pages, call Azure, or post to Teams or Slack.</dd>
        </div>
        <div>
          <dt>
            <code>--skip-teams</code>
          </dt>
          <dd>Skip the Teams webhook. Still print the console summary.</dd>
        </div>
        <div>
          <dt>
            <code>--skip-slack</code>
          </dt>
          <dd>Skip Slack even when the bot token and channel ID are set. Still print the console summary.</dd>
        </div>
        <div>
          <dt>
            <code>--max-urls</code>
          </dt>
          <dd>Cap how many compared candidates are fetched and extracted.</dd>
        </div>
      </dl>
      <pre>
        <code>{`python main.py --days 7
python main.py --dry-run
python main.py --skip-teams
python main.py --skip-slack
python main.py --days 7 --max-urls 3`}</code>
      </pre>

      <h2>Tests</h2>
      <p>From the repo root, with the virtual environment active:</p>
      <pre>
        <code>python -m pytest tests -q</code>
      </pre>
    </main>
  );
}
