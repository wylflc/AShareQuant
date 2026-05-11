# AShareQuant Agent Instructions

## Project Focus

AShareQuant is a research and data-analysis project for listed companies in mainland China and Hong Kong markets. Treat the latest user request and committed project docs as the source of truth for current priorities; do not turn transient requirements into reusable skill rules.

## Working Rules

- Read relevant files before editing, especially `README.md`, `CONTEXT.md`, existing ADRs, and nearby code.
- Keep changes scoped to the requested task and match the repository's existing style.
- Do not add dependencies, data providers, databases, schedulers, or external services unless the request clearly needs them.
- After any completed file-change batch, create a git commit before the final response. Do not push unless explicitly asked.
- Never store API keys, tokens, cookies, account identifiers, or paid-data credentials in the repository.

## Research And Data Principles

- Separate security-level concepts from company-level concepts. A listed company can have multiple securities, share classes, exchanges, or identifiers.
- Separate business-quality screening from valuation. A company can enter a watchlist because of durable business advantages even when its current price is unattractive.
- Preserve source provenance for market and fundamental data: provider, retrieval time, raw identifier, reporting period, currency, exchange, and adjustment policy where applicable.
- Prefer an auditable data flow: raw source records first, normalized records second, derived signals last.
- Treat corporate actions, dividends, split/bonus events, trading calendars, suspension days, and currency as first-class data concerns for equity analysis.
- For financial reports, distinguish reporting period, forecast/pre-announcement dates, official announcement dates, and the reported financial contents.

## Validation

- Run the most targeted useful check after changes: tests, lint, typecheck, build, or a small deterministic data/sample validation.
- If a check depends on network access, paid credentials, or unavailable market-data services, say so clearly and validate the local parts instead.
- Do not claim data coverage or analysis correctness unless it has been verified with reproducible checks.
