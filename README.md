# Sherlock

> **Pre-call research briefs for revenue teams. Free. Open-source. Built on Claude.**

Paste a LinkedIn profile. Drop in a company URL. Get a board-ready, one-page pre-call brief in under 60 seconds.

```
$ sherlock brief --interactive

  Paste the LinkedIn profile text below.
  > [paste]
  Company URL or domain: acme.com
  Meeting context: 30-min discovery call about scaling AE onboarding

  ✓ Parsing LinkedIn paste...
  ✓ Fetching acme.com...
  ✓ Enriching with Apollo...
  ✓ Generating brief sections (parallel)...

  Brief saved to brief.md
```

## What's in a brief

Every brief Sherlock generates contains the same seven sections, in the order a rep actually reads them:

1. **TL;DR** — who you're meeting and why it matters, in two sentences
2. **Company snapshot** — what they do, who they sell to, size, recent direction
3. **Their role** — current scope, prior background, decision-making signals
4. **Three things in their world right now** — recent moves, news, stated priorities
5. **Three opening questions** — grounded in something specific, never generic
6. **Three discovery questions** — designed to surface real buying signals
7. **Watch for** — one risk flag the seller shouldn't miss

See [`examples/sample-brief.md`](./examples/sample-brief.md) for a full example.

The sections live in [`src/sherlock/prompts/`](./src/sherlock/prompts/) as plain markdown files. Override any of them to match your team's playbook. See [Customizing prompts](#customizing-prompts) below.

## Why we built this

Pre-call research is the highest-frequency, lowest-leverage task in B2B sales. Every AE does it. Most do it badly because they're rushed. Their managers know it. Their CROs definitely know it.

Sherlock is the tool we wished existed: a sharp, single-purpose CLI that turns the public information you already have into a brief sharp enough to walk into a board meeting with.

It's free, open-source, and uses your own API keys — nothing about your prospect leaves your machine except the Claude API call.

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

Sherlock will walk you through pasting a LinkedIn profile, entering the company URL, and generating the brief. The result lands in `brief.md` in your working directory.

### Power-user mode

Once you've used the interactive flow once, the explicit form is faster:

```bash
sherlock brief \
  --linkedin-file profile.txt \
  --company acme.com \
  --context "30-min discovery call about their move to product-led growth" \
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

Output format is inferred from the `--out` extension. `.md` for markdown, `.html` for a styled standalone page suitable for screenshotting and sharing.

## Bring your own keys

| Variable | Required | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API access (Sonnet 4.6 by default). |
| `APOLLO_API_KEY` | Optional | Enrich with Apollo.io firmographics + person data. Skip per-call with `--no-apollo`. |
| `SHERLOCK_MODEL` | Optional | Override the Claude model. Default: `claude-sonnet-4-6`. |
| `SHERLOCK_MAX_TOKENS` | Optional | Max tokens per brief section. Default: `1500`. |
| `SHERLOCK_PROMPTS_DIR` | Optional | Path to a directory of overridden prompt templates. |

Drop these in a `.env` file in your working directory and Sherlock will pick them up automatically. See [`.env.example`](./.env.example).

**Nothing about your prospect leaves your machine** except (a) the API call to Anthropic and (b) the optional API call to Apollo. There is no Sherlock cloud, no telemetry, no analytics.

## On LinkedIn data

Sherlock takes pasted LinkedIn profile text by design — not scraped HTML. We do this because automated LinkedIn scraping is a ToS violation that puts your account at risk. Pasting the page text yourself is permitted, takes ten seconds, and yields the same downstream brief quality.

If you want to run a higher-volume workflow, point Sherlock at Apollo for person enrichment instead. Apollo handles the contact intelligence layer cleanly under their own data licensing. Sherlock will automatically blend Apollo data into the dossier when `APOLLO_API_KEY` is set.

## Apollo enrichment

When `APOLLO_API_KEY` is present, Sherlock makes two enrichment calls:

- **`POST /v1/organizations/enrich`** — pulls firmographics from the company domain: industry, employee count, annual revenue band, founding year, technology stack, and a short description.
- **`POST /v1/people/match`** — pulls a person record by name + company domain: title, seniority, location, employment history, LinkedIn URL.

Both data blocks get folded into the dossier passed to Claude, so every section of the brief is grounded in both your paste *and* Apollo's structured data. Apollo failures are non-fatal — Sherlock will warn and continue with paste-only data.

To skip Apollo for a single call (faster, cheaper, fully offline-respecting):

```bash
sherlock brief --no-apollo --linkedin-file profile.txt --company acme.com
```

## Customizing prompts

Every section of the brief is a single markdown file in [`src/sherlock/prompts/`](./src/sherlock/prompts/). Each file uses one placeholder, `{{research}}`, where the dossier gets injected.

To customize:

```bash
# 1. Copy the bundled prompts to a directory you control
mkdir -p ~/.sherlock/prompts
python -c "import sherlock.prompts, shutil, os; src=os.path.dirname(sherlock.prompts.__file__); [shutil.copy(os.path.join(src,f), os.path.expanduser('~/.sherlock/prompts/')) for f in os.listdir(src) if f.endswith('.md')]"

# 2. Edit any of them to match your team's playbook
$EDITOR ~/.sherlock/prompts/06_discovery_questions.md

# 3. Tell Sherlock to use your overrides
export SHERLOCK_PROMPTS_DIR=~/.sherlock/prompts
```

Common customizations:

- **Industry-specific discovery** — rewrite `06_discovery_questions.md` to surface signals around your specific category (security, fintech, healthcare).
- **Manager-flavored opening** — rewrite `05_opening_questions.md` for executive-level conversations vs. practitioner-level conversations.
- **Internal context block** — add a system instruction to the top of every prompt that frames who *you* sell, so the brief is generated against your specific value prop.

## Sherlock for teams

The CLI is built for individuals. If you want to roll Sherlock out across a whole sales org — with shared prompt libraries, hosted UI, CRM integration, and your own brand on the rendered briefs — see [`docs/enterprise.md`](./docs/enterprise.md) or [book a 30-min scoping call](https://performancelabs.ai).

## Roadmap

- **v0.2** — Hosted gallery (`sherlock --share` uploads to a public URL with a one-click "remove" link)
- **v0.3** — PDF render target via WeasyPrint
- **v0.4** — Multi-contact account briefs (research the buying committee, not just one person)
- **v0.5** — HubSpot + Salesforce push: write the brief into the contact record as a note

## Contributing

PRs welcome on bugs, prompt improvements, and new render targets. See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Big features — please open an issue first to talk through the design.

## License

MIT. Use it however you want.

---

**Built by [PerformanceLabs.AI](https://performancelabs.ai).** We help revenue teams ship AI tools that actually move pipeline. If that sounds like a problem you have, [reach out](https://performancelabs.ai).
