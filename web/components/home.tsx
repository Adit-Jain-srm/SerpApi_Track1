const GUIDE_HREF = "/guide";
const GITHUB_HREF = "https://github.com/Adit-Jain-srm/SerpApi_Track1";

const features = [
  {
    name: "A date window, not a hope",
    text: "Google web search takes SerpApi’s tbs=qdr:dN. Google News takes after:YYYY-MM-DD. Both stay inside the days you pass.",
  },
  {
    name: "Two engines, one list",
    text: "Web and news run together. The same URL collapses to one row. When the dates disagree, the news date wins.",
  },
  {
    name: "Articles point at products",
    text: "A launch post that names one product homepage is fetched next. The digest keeps that homepage. A listicle that names five products is dropped.",
  },
  {
    name: "A card, not a paragraph",
    text: "Each kept page becomes title, audience, summary, features, pricing, and source. The console prints it. Slack or Teams can post it.",
  },
];

export function Home() {
  return (
    <main className="home">
      <header className="mast">
        <p className="mast-name">AI Tool Discovery Agent</p>
        <p className="mast-edition">Weekly digest</p>
      </header>
      <div className="rules" aria-hidden="true">
        <span className="rule-ink" />
        <span className="rule-red" />
      </div>

      <section className="spread" aria-labelledby="claim">
        <div className="spread-copy">
          <p className="kicker">For teams who ship against new tools</p>
          <h1 id="claim">
            Find the AI products that launched this week. Leave the roundups in the search results.
          </h1>
          <p className="lede">
            The agent plans a date window, searches SerpApi, compares web and news, and posts a card to the console, Slack, or Microsoft Teams.
          </p>
          <div className="actions">
            <a className="control" href={GUIDE_HREF}>
              Read the guide
            </a>
            <a className="text-link" href={GITHUB_HREF} rel="noreferrer">
              Source on GitHub
            </a>
          </div>
        </div>
        <figure className="plate">
          <img
            src="/teams_output_example.png"
            width={1024}
            height={506}
            alt="Sample digest card: title, website, audience, overview, features, pricing, and source."
          />
          <figcaption>Sample of the card shape. Not a discovery from today.</figcaption>
        </figure>
      </section>

      <section className="band" aria-labelledby="useful">
        <h2 id="useful">Who it is for</h2>
        <div className="useful">
          <p>
            A team lead who needs to know what shipped, not what a blog ranked. A researcher who wants the product page, not the article about the product page. A developer advocate who would rather get one card than forty tabs.
          </p>
          <p>
            The useful part is the rejection. Search returns launch lists, museum pages, and news. The digest keeps a product: what it does, who it is for, what it costs, and where it lives.
          </p>
        </div>
      </section>

      <section className="band" aria-labelledby="features">
        <h2 id="features">What a run actually does</h2>
        <ol className="feature-list">
          {features.map((feature, index) => (
            <li key={feature.name}>
              <span className="feature-num">{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h3>{feature.name}</h3>
                <p>{feature.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="band" aria-labelledby="arch">
        <h2 id="arch">Architecture</h2>
        <p className="band-note">
          Ten searches. Four announcement queries on web and news, two homepage queries on web only. Then a capped hop from an article to the product it names.
        </p>
        <div className="diagram" role="img" aria-label="Plan, search web and news, compare, fetch, extract, then console, Slack, or Teams.">
          <svg viewBox="0 0 960 220" className="arch">
            <title>Pipeline</title>
            {[
              ["Plan", 70],
              ["Web", 210],
              ["News", 340],
              ["Compare", 490],
              ["Fetch", 640],
              ["Extract", 790],
            ].map(([label, x]) => (
              <g key={label}>
                <rect x={Number(x) - 58} y="36" width="116" height="44" />
                <text x={x} y="64">
                  {label}
                </text>
              </g>
            ))}
            <path d="M128 58 H152 M268 58 H282 M398 58 H432 M548 58 H582 M698 58 H732" />
            <text x="210" y="28" className="diagram-tag">
              google · tbs
            </text>
            <text x="340" y="28" className="diagram-tag">
              google_news · after:
            </text>
            <g>
              <rect x="250" y="130" width="460" height="52" />
              <text x="480" y="162">
                Console, or Slack, or Teams
              </text>
            </g>
            <path d="M790 80 V130" />
          </svg>
        </div>
      </section>

      <section className="band" aria-labelledby="robust">
        <h2 id="robust">What happens when a step fails</h2>
        <ul className="robust">
          <li>
            <strong>One engine fails.</strong>
            <span>The other engine’s rows are kept. The run continues.</span>
          </li>
          <li>
            <strong>Both engines fail.</strong>
            <span>The process exits with an error. It does not print an empty success.</span>
          </li>
          <li>
            <strong>A page returns 403, or robots.txt says no.</strong>
            <span>That URL is skipped. The rest of the batch continues.</span>
          </li>
          <li>
            <strong>The page is an article.</strong>
            <span>If it names one product site, that site is fetched. If it names several, it is a roundup and it is dropped.</span>
          </li>
          <li>
            <strong>Slack or Teams is unset.</strong>
            <span>That delivery is skipped. The console still prints the cards.</span>
          </li>
          <li>
            <strong>Dry run.</strong>
            <span>Search and compare only. No fetch, no extraction, no post.</span>
          </li>
        </ul>
      </section>

      <section className="band close" aria-labelledby="output">
        <h2 id="output">The thing you receive</h2>
        <p className="band-note">
          Title, website, audience, overview, features, pricing, source. The same fields in the terminal and in Slack.
        </p>
        <figure className="plate plate-end">
          <img
            src="/teams_output_example.png"
            width={1024}
            height={506}
            alt="The same sample digest card, shown again at the end of the page."
          />
          <figcaption>
            <a href={GUIDE_HREF}>Read the guide</a>
            <span aria-hidden="true"> · </span>
            <a href={GITHUB_HREF} rel="noreferrer">
              GitHub
            </a>
          </figcaption>
        </figure>
      </section>
    </main>
  );
}
