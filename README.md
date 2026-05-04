# Sherlock

> **Pre-call research briefs for revenue teams. Free. Open-source. Built on Claude.**

Paste a LinkedIn profile. Drop in a company URL. Get a board-ready, two-to-three-page pre-call brief with every claim source-tagged.

```
$ sherlock brief --interactive

  Paste the LinkedIn profile text below.
  > [paste]
  Company URL or domain: acme.com
  Meeting context: 30-min discovery call about scaling AE onboarding
  Your positioning: Sales enablement platform that compresses AE ramp time

  ✓ Parsing LinkedIn paste...
  ✓ Fetching acme.com...
  ✓ Researching across web sources (news, funding, jobs, interviews, LinkedIn company)...
  ✓ Generating sections 1-7 and 9 in parallel...
  ✓ Synthesizing psychographic profile from prior sections...
  ✓ Validating confidence tags...

  Brief saved to brief.md  (9 sources gathered)
```

See it rendered: **[sherlock-demo.vercel.app](https://sherlock-demo.vercel.app)** (a sample brief on a fictional prospect).

**Try the live app: [sales-sherlock-app.vercel.app](https://sales-sherlock-app.vercel.app)** — paste a real LinkedIn profile, get a real brief in ~60 seconds. Bring your own Anthropic API key via the form-based UI.

## What's in a brief

Sherlock produces nine sections, in the order an account executive actually reads them:

1. **Company Overview** — what they do, who they serve, size, stage
2. **Company History** — founding, inflection points, recent material changes
3. **Investment and Ownership** — funding, investors, M&A, what the structure implies for buying style
4. **Growth and Revenue Signals** — hiring patterns, traction, operational pressure (urgency tells)
5. **Industry and Competitive Landscape** — category position, named competitors, industry pressures
6. **Contact Professional Profile** — current role, career arc, education, rapport hooks if you supplied positioning
7. **Contact Personal and Public Profile** — geography, public interests, public causes (only what's public)
8. **Psychographic and Decision-Making Profile** — DISC read, decision pattern, communication style, likely buying style. Generated *last*, after the other 8 sections, so it's synthesis rather than parallel pattern-matching.
9. **Conversational Hooks and Risks** — rapport hooks, topics to handle carefully, open questions for the call

Every factual claim carries a confidence tag:

- **`[Verified - S3]`** sourced from a primary or authoritative source (cite by ID)
- **`[Reported - S2]`** widely reported in secondary sources
- **`[Inferred]`** your model's interpretation, not fact

The brief ends with a numbered Sources index so the inline citations resolve. See [`examples/sample-brief.md`](./examples/sample-brief.md) for a full example.

The prompts live in [`src/sherlock/prompts/`](./src/sherlock/prompts/) as plain markdown. Override any of them to match your team's playbook. See [Customizing prompts](#customizing-prompts) below.

## Why we built this

Pre-call research is the highest-frequency, lowest-leverage task in B2B sales. Every AE does it. Most do it badly because they're rushed. Their managers know it. Their CROs definitely know it.

Sherlock is the tool we wished existed: a sharp, single-purpose CLI that turns the public information you already have into a brief sharp enough to walk into a board meeting with. Confidence tags make the brief honest. The two-stage pipeline (research first, write second, synthesize psychographics last) makes it dense.

It's free, open-source, and uses your own API keys. Available as a Python CLI and a hosted web app.

## Two ways to use Sherlock

| | CLI | Web app |
|---|---|---|
| Where it runs | Your laptop | Vercel-hosted at [sales-sherlock-app.vercel.app](https://sales-sherlock-app.vercel.app) |
| Setup | `pipx install sherlock-brief` + `ANTHROPIC_API_KEY` env var | Open the URL |
| Output | `brief.md` or `brief.html` on disk | Rendered in-browser, copy/download/print |
| Customizable prompts | Yes via `SHERLOCK_PROMPTS_DIR` | Not yet |
| Best for | Power users, scripting, CI workflows | First-time users, one-off briefs, sharing with non-technical teammates |

The CLI is the canonical interface. The web app is the same pipeline (same nine sections, same confidence tags, same source registry) wrapped in a form, with the orchestration split across short serverless functions to fit Vercel's 60-second function ceiling.

## Install

```bash
# Recommended: isolated install via pipx
pipx install sherlock-brief

# Or via pip into your current env
pip install sherlock-brief
```

That gives you the `sherlock` command. Verify:

```bash
sherlock --version
```

## Quick start

Set your Anthropic API key (get one at https://console.anthropic.com):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Then:

```bash
sherlock brief --interactive
```

Sherlock will walk you through pasting a LinkedIn profile, entering the company URL, the meeting context, and your own positioning. The result lands in `brief.md` in your working directory.

### Power-user mode

Once you've used the interactive flow once, the explicit form is faster:

```bash
sherlock brief \
  --linkedin-file profile.txt \
  --company acme.com \
  --context "30-min discovery call about their move to product-led growth" \
  --positioning "Sales enablement platform that compresses AE ramp time" \
  --out briefs/acme-jane-doe.md
```

Or pipe the LinkedIn paste in from your clipboard:

```bash
# macOS
pbpaste | sherlock brief --linkedin-stdin --company acme.com --out brief.md

# Windows PowerShell
Get-Clipboard | sherlock brief --linkedin-stdin --company acme.com --out brief.md

# Linux (with xclip)
xclip -o | sherlock brief --linkedin-stdin --company acme.com --out brief.md
```

Output format is inferred from the `--out` extension. `.md` for markdown, `.html` for a styled standalone page with confidence-tag pills and a clickable sources index.

### Flags worth knowing

| Flag | What it does |
|---|---|
| `--positioning` / `-p` | Your own value prop. Sherlock uses it to flag rapport hooks based on shared background. |
| `--min-paste-chars` / `-M` | Minimum LinkedIn paste size (default 800). Below this, Sherlock refuses rather than producing a thin brief. |
| `--no-web-search` | Skip the research stage. Brief sourced only from the LinkedIn paste and the company website. Faster, cheaper, less complete. |
| `--no-apollo` | Skip Apollo enrichment even if `APOLLO_API_KEY` is set. |
| `--model` / `-m` | Override the Claude model (default: `claude-sonnet-4-6`). |

## Why we ask for a LinkedIn paste

LinkedIn blocks automated profile fetching, so a profile URL alone usually returns nothing useful. Asking you to paste the visible page text directly gives Sherlock the actual source material to work from.

**Paste generously.** The brief quality is bounded by the paste quality. Include: headline, About, full Experience history, Education, Skills, Recommendations if visible, and the most recent 5 to 10 posts or reposts. The more raw text, the stronger the psychographic read.

If your paste is thin, Sherlock will refuse rather than producing a weak brief. You can lower `--min-paste-chars` to override, but quality will suffer.

## Bring your own keys

| Variable | Required | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API access (Sonnet 4.6 by default). Also powers Anthropic-hosted web search. |
| `APOLLO_API_KEY` | Optional | Enrich with Apollo.io firmographics + person data. Skip per-call with `--no-apollo`. |
| `SHERLOCK_MODEL` | Optional | Override the Claude model. Default: `claude-sonnet-4-6`. |
| `SHERLOCK_MAX_TOKENS` | Optional | Max tokens per brief section. Default: `1500`. |
| `SHERLOCK_PROMPTS_DIR` | Optional | Path to a directory of overridden prompt templates. |
| `SHERLOCK_NO_WEB_SEARCH` | Optional | Set to any value to skip the research stage entirely. |

Drop these in a `.env` file in your working directory and Sherlock will pick them up automatically. See [`.env.example`](./.env.example).

**Nothing about your prospect leaves your machine** except (a) Claude API calls and (b) the optional Apollo call. Web search uses Anthropic's hosted tool, which goes through the same API key. There is no Sherlock cloud, no telemetry, no analytics.

## How the pipeline works

Sherlock runs in two stages.

**Stage 1 — Research.** In parallel, Sherlock dispatches targeted Anthropic-hosted web searches across:

- **News and press** — leadership changes, product launches, layoffs, controversies
- **Funding and ownership** — Crunchbase, PitchBook, SEC, lead investors, M&A
- **Open jobs** — what's being hired, which technologies, which seniority levels
- **Interviews** — podcasts, conference talks, op-eds by the contact
- **LinkedIn company page** — official headcount, growth signal, recent activity

Each finding becomes a Source record with a stable ID (`S1`, `S2`, ...). The dossier handed to the writing stage includes the full numbered source index.

**Stage 2 — Writing.** Sections 1 through 7 and 9 generate in parallel against the dossier. Each section is run through a confidence-tag validator; if a section comes back missing tags, Sherlock runs a single repair pass on just that section.

Section 8 (Psychographic and Decision-Making Profile) generates **last, sequentially**, with the other eight sections passed in as additional context. This is deliberate. Psychographics is synthesis, not parallel pattern-matching, and giving the model a view of the company history, ownership structure, career arc, and conversational hooks before asking for the read produces a sharper brief than running it in parallel.

## Apollo enrichment

When `APOLLO_API_KEY` is present, Sherlock makes two enrichment calls:

- **`POST /v1/organizations/enrich`** — pulls firmographics from the company domain: industry, employee count, annual revenue band, founding year, technology stack.
- **`POST /v1/people/match`** — pulls a person record by name + company domain: title, seniority, location, employment history, LinkedIn URL.

Both data blocks get folded into the dossier passed to Claude. Apollo failures are non-fatal — Sherlock will warn and continue with paste-only data.

To skip Apollo for a single call:

```bash
sherlock brief --no-apollo --linkedin-file profile.txt --company acme.com
```

## Customizing prompts

Every section of the brief is a single markdown file in [`src/sherlock/prompts/`](./src/sherlock/prompts/). Each file uses up to three placeholders:

- `{{sources}}` — the numbered source index
- `{{research}}` — the full dossier as XML
- `{{prior_sections}}` — only the psychographic prompt sees this; it's the rendered output of the other 8 sections

To customize:

```bash
# 1. Copy the bundled prompts to a directory you control
mkdir -p ~/.sherlock/prompts
python -c "import sherlock.prompts, shutil, os; src=os.path.dirname(sherlock.prompts.__file__); [shutil.copy(os.path.join(src,f), os.path.expanduser('~/.sherlock/prompts/')) for f in os.listdir(src) if f.endswith('.md')]"

# 2. Edit any of them to match your team's playbook
$EDITOR ~/.sherlock/prompts/08_psychographic.md

# 3. Tell Sherlock to use your overrides
export SHERLOCK_PROMPTS_DIR=~/.sherlock/prompts
```

Common customizations:

- **Industry-specific psychographics** — rewrite `08_psychographic.md` to surface signals around your specific category (security, fintech, healthcare).
- **Manager-flavored hooks** — rewrite `09_hooks_and_risks.md` for executive-level conversations vs. practitioner-level conversations.
- **Internal context block** — add a system instruction to the top of every prompt that frames who *you* sell, so the brief is generated against your specific value prop.

## Web app architecture

The live app at [sales-sherlock-app.vercel.app](https://sales-sherlock-app.vercel.app) is deployed from this repo. It's the CLI's pipeline, restructured into short serverless functions so each call stays under the Vercel Hobby 60-second timeout:

- **`api/research.py`** — paste validation, LinkedIn parse, company website fetch, optional Apollo enrichment. No LLM. ~3 seconds.
- **`api/search.py`** — one Anthropic-hosted `web_search` call for one source category (news, funding, jobs, LinkedIn company, or interviews). Uses `claude-haiku-4-5` so its token usage doesn't compete with the writing stage's Sonnet pool. ~10 seconds.
- **`api/section.py`** — one prompt-per-section against the assembled dossier, plus the per-section confidence-tag validator and one-shot repair pass. ~10 seconds.
- **`api/render.py`** — pure render, no LLM. Returns HTML or markdown.
- **`api/health.py`** — env-var probe used by the frontend on load.

The frontend (vanilla HTML + JS in `public/`) orchestrates: research → 5 batched searches (2 at a time) → 8 batched section writes (3 at a time) → sequential psychographic synthesis → render. Batching is calibrated to stay under the 30K-input-tokens-per-minute developer-tier Anthropic rate limit.

Configuration: see `vercel.json` for per-function timeouts, `requirements.txt` for the deploy environment, and `pyproject.toml` for the package itself (FastAPI + Pydantic are required deps because Vercel's uv-based Python builder reads required deps from `pyproject.toml`).

## Roadmap

- **v0.2** — Hosted gallery (`sherlock --share` uploads to a public URL with a one-click "remove" link)
- **v0.3** — PDF render target via WeasyPrint
- **v0.4** — Multi-contact account briefs (research the buying committee, not just one person)
- **v0.5** — HubSpot + Salesforce push: write the brief into the contact record as a note

## Contributing

PRs welcome on bugs, prompt improvements, and new render targets. See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Big features — please open an issue first to talk through the design.

## License

MIT. Use it however you want.
