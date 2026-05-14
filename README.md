# AShareQuant

AShareQuant is a research and data-analysis project for listed companies in mainland China, Hong Kong, and U.S. equity markets.

The project is intended to support a reproducible equity-research workflow: build an investable universe, identify companies worth following based on durable business quality, collect market and fundamental data, and keep the analysis auditable over time.

## Scope

- Build and maintain universes for A-share, Hong Kong, and U.S. listed securities.
- Distinguish listed companies from their tradable securities, share classes, exchanges, and identifiers.
- Screen listed companies for durable business advantages before any valuation decision.
- Track watchlists as research outputs, not as buy recommendations.
- Collect historical market data including daily open, high, low, close, volume, and related trading fields.
- Track corporate actions such as dividends, splits, bonus shares, rights issues, and other events that affect historical comparability.
- Collect financial report data and disclosure timelines, including forecast, pre-announcement, and official announcement dates where available.

## Principles

- Keep raw source records separate from normalized data and derived signals.
- Preserve data provenance: provider, retrieval time, raw identifier, exchange, currency, reporting period, and adjustment policy.
- Treat trading calendars, suspensions, corporate actions, and identifier mapping as first-class data concerns.
- Keep business-quality screening separate from valuation assessment.
- Avoid committing credentials, paid-data access details, cookies, or private account identifiers.

## Project Docs

- `AGENTS.md` contains repository-specific instructions for coding agents.
- `CONTEXT.md` defines the stable domain language used by the project.
- `.agents/skills/equity-research-workflow/SKILL.md` contains reusable workflow guidance for future agent work in this repository.
- `.agents/` and `.codex/` are local agent workspaces and are intentionally ignored by Git.

## Development Workflow

Read the project docs before making changes. After modifying files, run the most targeted useful local check available and commit the completed change batch. Do not push to a remote unless explicitly requested.

## Scripts

Fetch the current mainland China A-share security universe:

```bash
python3 scripts/fetch_a_share_universe.py --output data/raw/a_share_securities.csv
```

The CSV records security code, exchange, board, listed-company name, security name, listing date, industry, region, source provider, retrieval time, and raw provider identifier useful for later screening.

Fetch the current Hong Kong listed equity security universe:

```bash
python3 scripts/fetch_hong_kong_universe.py --output data/raw/hong_kong_securities.csv
```

The Hong Kong CSV is security-level and keeps separate counters, share classes, and trading currencies as separate **Hong Kong Securities**.

Fetch the current U.S. listed security universe:

```bash
python3 scripts/fetch_us_universe.py --output data/raw/us_securities.csv
```

The U.S. CSV combines Nasdaq Trader `nasdaqlisted.txt` and `otherlisted.txt`, excludes provider test issues by default, and keeps ETF/status/exchange fields for later screening.

Run the legacy first-pass moat screening for A-share and Hong Kong securities:

```bash
python3 scripts/run_moat_screening.py
```

This legacy script reads manually curated evidence from `data/interim/moat_screening_evidence.csv` and writes `data/processed/moat_watchlist_candidates.csv`. That candidate file is kept for audit/history, but it is not the canonical current watchlist. Use the full-coverage market-specific outputs below for current A-share, Hong Kong, and U.S. screening.

The screening workflow keeps `data/raw/` immutable. Source-backed research evidence belongs in `data/interim/`; generated screening outputs belong in `data/processed/`.

For the A-share, Hong Kong, and U.S. universes, the target workflow is a **Full-Coverage Screening Run**: every listed security receives an explicit screening status, and every eligible listed-company common-equity security receives the same dimensional scoring treatment unless it meets the narrow **Insufficient Disclosure** definition. The current scoring model is `full_coverage_dimensional_v0.3`, with seven dimensions: business moat, technology/product/process barrier, market position, business quality, operating quality, industry outlook/cyclicality/compounding profile, and governance risk. Each dimension score and final weighted score is stored with two decimal places. See `docs/moat-scoring-rubric.md` and `docs/adr/0002-use-full-coverage-dimensional-moat-scoring.md`.

Fetch A-share screening evidence into resumable interim CSV files:

```bash
python3 scripts/fetch_a_share_research_evidence.py
```

The fetcher writes `data/interim/a_share_research_queue.csv`, `data/interim/a_share_company_profiles.csv`, and `data/interim/a_share_financial_indicators.csv`.

Generate dimensional A-share scores from fetched evidence:

```bash
python3 scripts/run_a_share_full_coverage_scoring.py
```

The scorer writes `data/processed/a_share_full_coverage_scores.csv` and `data/processed/a_share_full_coverage_watchlist.csv`. The outputs include `cyclicality_profile`, `compounding_profile`, and `industry_outlook_*` fields so cyclicals and compound-growth companies can be reviewed separately. Use `--require-complete` when the fetch queue is complete and the run should fail if any eligible A-share company remains unscored.

Fetch Hong Kong screening evidence into resumable interim CSV files:

```bash
python3 scripts/fetch_hong_kong_research_evidence.py
```

The fetcher writes `data/interim/hong_kong_research_queue.csv`, `data/interim/hong_kong_company_profiles.csv`, and `data/interim/hong_kong_financial_indicators.csv`. It uses Eastmoney HKF10 first and falls back to ETNet company information for newly listed securities that are not yet covered by Eastmoney.

Generate dimensional Hong Kong scores from fetched evidence:

```bash
python3 scripts/run_hong_kong_full_coverage_scoring.py
```

The scorer writes `data/processed/hong_kong_full_coverage_scores.csv` and `data/processed/hong_kong_full_coverage_watchlist.csv`. The Hong Kong outputs explicitly include `market_type`, `market_label`, `cyclicality_profile`, `compounding_profile`, and `industry_outlook_*` fields so they can be merged with other markets later without losing market identity or cycle/compound-growth context.

Fetch U.S. screening evidence into resumable interim CSV files:

```bash
python3 scripts/fetch_us_research_evidence.py
```

The fetcher writes `data/interim/us_research_queue.csv`, `data/interim/us_company_profiles.csv`, and `data/interim/us_financial_indicators.csv`. It uses Nasdaq Trader for the raw security universe and SEC EDGAR `company_tickers`, `submissions`, and `companyfacts` for company profile and financial evidence. ETF, ETN, unit, warrant, right, preferred, closed-end fund, and other non-common-equity instruments are kept in the output with an explicit not-applicable status rather than being scored as listed companies. Use `--symbols UNH,MSFT` to refresh a targeted subset without rewriting unrelated evidence rows.

Generate dimensional U.S. scores from fetched evidence:

```bash
python3 scripts/run_us_full_coverage_scoring.py
```

The scorer writes `data/processed/us_full_coverage_scores.csv` and `data/processed/us_full_coverage_watchlist.csv`. The U.S. outputs explicitly include `market_type`, `market_label`, `cyclicality_profile`, `compounding_profile`, and `industry_outlook_*` fields for later cross-market merging.
