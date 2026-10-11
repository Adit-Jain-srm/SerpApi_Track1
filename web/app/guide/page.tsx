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
        <a href="/">Weekly digest</a>
        <a href="/subscribe">Subscribe</a>
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
          Sample of the Teams card. Not a claim this tool was found today.
        </figcaption>
      </figure>
      <figure className="guide-still">
        <img
          src="/slack_output_example.png"
          width={1024}
          height={640}
          alt="Sample Slack digest in #tool-updates for SynthID Detector, posted by AI-Search-Buddy."
        />
        <figcaption>
          The same fields in Slack, when the bot token and channel are set.
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
      </ul>
      <p>
        <code>AZURE_OPENAI_DEPLOYMENT</code> selects the deployment. When it is empty, extraction uses <code>gpt-5.3-chat</code>.
      </p>
      <p>Optional:</p>
      <ul>
        <li>
          <code>TEAMS_WEBHOOK_URL</code>. Leave it empty to print the console summary and skip Teams.
        </li>
        <li>
          <code>SLACK_BOT_TOKEN</code> and <code>SLACK_CHANNEL_ID</code>. Leave either empty to skip Slack. Posting needs both.
        </li>
        <li>
          <code>SUPABASE_URL</code>, <code>SUPABASE_SECRET_KEY</code>, and <code>NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY</code>. Configures PostgreSQL subscriber delivery with Row-Level Security.
        </li>
      </ul>
      <p>
        <code>--dry-run</code> needs <code>SERPAPI_API_KEY</code>. It does not need the Azure names, and it does not call Azure.
      </p>

      <h2>Health Check & Diagnostics</h2>
      <p>To verify all credentials, search quotas, database connection, and latency before running:</p>
      <pre>
        <code>{`python main.py --doctor
# or standalone:
python check_apis.py`}</code>
      </pre>

      <h2>Run</h2>
      <p>From the repo root, with the virtual environment active:</p>
      <pre>
        <code>python main.py</code>
      </pre>

      <h2>Flags</h2>
      <dl className="guide-flags">
        <div>
          <dt>
            <code>--doctor</code>
          </dt>
          <dd>Verify connectivity and latency for SerpApi, Azure OpenAI, Supabase, and Slack before running.</dd>
        </div>
        <div>
          <dt>
            <code>--days</code>
          </dt>
          <dd>Date window in days. Default 7, or SEARCH_DAYS when the flag is omitted. Must be a positive integer.</dd>
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
            <code>--skip-subscribers</code>
          </dt>
          <dd>Do not deliver the digest to signed-in Supabase subscribers.</dd>
        </div>
        <div>
          <dt>
            <code>--max-urls</code>
          </dt>
          <dd>Cap how many compared candidates are fetched and extracted. Must be a positive integer.</dd>
        </div>
      </dl>
      <pre>
        <code>{`python main.py --doctor
python main.py --days 7
python main.py --dry-run
python main.py --skip-teams
python main.py --skip-slack
python main.py --skip-subscribers
python main.py --days 7 --max-urls 3
python main.py --days 7 --max-urls 3 --skip-teams --skip-slack --skip-subscribers`}</code>
      </pre>

      <h2>Edge cases</h2>
      <ul>
        <li>
          <code>--days 0</code> and a negative <code>--days</code> exit with code 2. The message is <code>--days must be a positive integer</code>. There is no traceback and no search.
        </li>
        <li>
          <code>--max-urls 0</code> and a negative <code>--max-urls</code> exit with code 2. The message is <code>--max-urls must be a positive integer</code>. The run does not print an empty table.
        </li>
        <li>If one search engine fails, the run continues with the other. If both fail, the process exits non-zero.</li>
        <li>
          <code>--dry-run</code> prints the comparison table and stops before fetch.
        </li>
        <li>A missing Teams webhook, or <code>--skip-teams</code>, skips Teams. A missing Slack token or channel, or <code>--skip-slack</code>, skips Slack.</li>
        <li>Supabase subscriber webhooks must be valid HTTPS. Insecure endpoints are discarded.</li>
      </ul>

      <h2>Tests</h2>
      <p>From the repo root, with the virtual environment active:</p>
      <pre>
        <code>python -m pytest tests -v</code>
      </pre>
    </main>
  );
}
