# How Sherlock works

A short tour of what happens when you run `sherlock brief --interactive`.

## 1. Inputs

Sherlock takes three inputs:

- **A LinkedIn paste** — pasted text from the prospect's LinkedIn profile page (Cmd/Ctrl+A then Cmd/Ctrl+C in your browser).
- **A company URL or domain** — e.g. `acme.com`.
- **A meeting context** — a one-line description of what the call is about.

No browser automation, no LinkedIn scraping. The paste flow is deliberate — see [README.md > On LinkedIn data](../README.md#on-linkedin-data).

## 2. Building the dossier

`sherlock.sources.linkedin.parse_linkedin_paste` runs a few heuristics over the paste to extract a name, headline, current role, current company, location, and the About section. **The full raw paste is always preserved** — these parsed fields exist mainly so we can pass clean values to Apollo.

`sherlock.sources.web.fetch_company_summary` makes an HTTP request to the company URL, parses the HTML with BeautifulSoup, and pulls the page title, meta description, and a capped slice of the visible body text.

If `APOLLO_API_KEY` is set (and `--no-apollo` isn't passed), `sherlock.sources.apollo.enrich_with_apollo` makes two API calls — one to enrich the organization by domain, and one to match the person by name + domain. We pull a small, prompt-friendly subset of the response, not the whole record.

All three of these go into a `Dossier` dataclass and get rendered as a single XML block via `Dossier.to_research_block()`. That block is what every prompt sees.

## 3. Generating the brief

`sherlock.researcher.generate_brief` loads the seven prompt templates from `sherlock/prompts/` (or your `SHERLOCK_PROMPTS_DIR` override), substitutes the dossier into the `{{research}}` placeholder in each, and fires all seven Claude calls **in parallel** via `asyncio.gather`.

This is why Sherlock can produce a 7-section brief in 8-12 seconds instead of 60+. Each section is its own call, each call is independent, and the model handles each section without context from the others — which is fine because every section gets the same dossier as input.

## 4. Rendering

The seven section bodies come back as markdown strings. `sherlock.render.markdown.render_markdown` stitches them together with a header, separators, and a footer. `sherlock.render.html.render_html` does the same but wraps everything in a styled HTML template suitable for screenshots and shareable links.

The output extension on `--out` decides which renderer runs: `.md` → markdown, `.html` → HTML.

## 5. What you get

A single file, on disk, in your working directory. No telemetry. No upload. No history saved anywhere except where you save it.

## Cost per brief

Roughly:

- 7 Claude calls × ~3-5K input tokens × ~500-800 output tokens
- At Sonnet 4.6 list pricing, that's typically a few cents per brief
- Apollo's free tier covers ~50 enrichments/month before you hit a paywall

If you're running Sherlock at higher volume, switch to `claude-haiku-4-5-20251001` via `SHERLOCK_MODEL` for ~5-10x cost reduction at the cost of some depth.
