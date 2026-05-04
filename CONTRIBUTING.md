# Contributing to Sherlock

Thanks for considering a contribution. Sherlock stays sharp by staying small — we'd rather merge a tight prompt improvement than a sprawling new feature.

## What we're looking for

- **Prompt improvements.** If a section consistently produces weak output for a category of prospect, propose a better prompt and include 2-3 sample briefs (real or fictional, anonymized) showing the improvement.
- **Bug fixes.** Especially around the LinkedIn paste parser and Apollo enrichment edge cases.
- **New render targets.** PDF (via WeasyPrint), Notion, Slack canvas — happy to merge with reasonable scope.
- **Documentation clarity.** Real users hitting real confusion.

## What needs an issue first

- Net-new sections in the brief.
- Net-new data sources beyond Apollo.
- Web app / hosted UI changes.
- Anything that adds a paid-only dependency.

Open an issue, describe the use case, and we'll talk through the shape before you write code.

## Local setup

```bash
git clone https://github.com/tonybangert/sherlock
cd sherlock
pip install -e ".[dev]"
sherlock --version
```

## Code style

- Python 3.10+, type hints encouraged.
- `ruff` for linting and formatting (config in `pyproject.toml`).
- Keep the CLI dependency footprint small. If you're adding a new dependency, justify it in the PR description.

## Tests

We're light on tests right now (pre-1.0). If you're adding meaningful logic — a new parser, a new render target, an edge case in Apollo — add a test in `tests/` using `pytest`.

## License

By submitting a PR, you agree your contribution is licensed under MIT.
