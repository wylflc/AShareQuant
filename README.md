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

For the A-share, Hong Kong, and U.S. universes, the target workflow is now a **Two-Layer Company Review**. The first layer keeps full-universe coverage through baseline triage: every listed security receives an explicit screening status, and every eligible listed-company common-equity security receives a preliminary business-quality review unless it meets the narrow **Insufficient Disclosure** definition. The second layer performs a full **Deep Company Review** for companies with `triage_score >= 65`, companies marked `borderline`, and companies explicitly challenged by a reviewer.

The existing `full_coverage_dimensional_v0.4` scoring model is a baseline triage aid, not the final watchlist decision model. It has seven dimensions: business moat, technology/product/process barrier, market position, business quality, operating quality, industry outlook/cyclicality/compounding profile, and governance risk. Deep reviews must use authoritative research sources such as company periodic reports, exchange announcements, regulator disclosures, official investor-relations materials, reputable institution reports, or professional research reports. Aggregator company introductions are discovery hints only, not scoring evidence. See `docs/moat-scoring-rubric.md`, `docs/adr/0002-use-full-coverage-dimensional-moat-scoring.md`, and `docs/adr/0003-adopt-two-layer-company-review.md`.

Build the current two-layer company triage and second-layer deep-review queue:

```bash
python3 scripts/run_two_layer_company_review.py
```

The script reads the market-specific full-coverage score files and optional reviewer challenges from `data/interim/deep_review_challenges.csv`. It writes `data/processed/company_triage_reviews.csv` as the company-level first-layer triage output and `data/interim/deep_review_queue.csv` as the pending second-layer review queue. The queue is not a final watchlist; it is the auditable worklist for full deep reviews using authoritative sources. Reviewer-challenged companies enter the queue even when the baseline triage score is below the normal threshold.

During calibration, run markets separately. A-share is the first calibration market:

```bash
python3 scripts/run_two_layer_company_review.py --markets A_SHARE --triage-output data/processed/a_share_company_triage_reviews.csv --queue-output data/interim/a_share_deep_review_queue.csv
python3 scripts/audit_a_share_review_standard.py
```

The A-share run writes `data/processed/a_share_company_triage_reviews.csv` and `data/interim/a_share_deep_review_queue.csv`. The audit writes `data/processed/a_share_review_standard_audit.csv`, checking A-share-only scope, universe coverage, queue construction, score-band distribution, and reviewer-challenge routing. Passing this audit only validates the workflow structure. Reviewer-challenged companies are not calibration anchors merely because they were named; reusable rules should come from peer-group calibration, where similar companies in one industry are compared side by side before the reviewer decides which deserve continued attention.

The first A-share peer-group calibration output is baijiu:

- `data/processed/a_share_baijiu_peer_group_calibration.csv`
- `data/processed/a_share_baijiu_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-baijiu.md`

The second A-share peer-group calibration output is EV batteries and new-energy platforms:

- `data/processed/a_share_ev_battery_peer_group_calibration.csv`
- `data/processed/a_share_ev_battery_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-ev-battery.md`

The third A-share peer-group calibration output is high-end medical devices and medical-device platforms:

- `data/processed/a_share_medical_device_peer_group_calibration.csv`
- `data/processed/a_share_medical_device_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-medical-device.md`

The fourth A-share peer-group calibration output is listed banks:

- `data/processed/a_share_bank_peer_group_calibration.csv`
- `data/processed/a_share_bank_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-bank.md`

The fifth A-share peer-group calibration output is semiconductor equipment:

- `data/processed/a_share_semiconductor_equipment_peer_group_calibration.csv`
- `data/processed/a_share_semiconductor_equipment_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-semiconductor-equipment.md`

The sixth A-share peer-group calibration output is strategic resources and mining:

- `data/processed/a_share_strategic_resources_peer_group_calibration.csv`
- `docs/peer-group-calibration/a-share-strategic-resources.md`

Fetch A-share screening evidence into resumable interim CSV files:

```bash
python3 scripts/fetch_a_share_research_evidence.py
```

The fetcher writes `data/interim/a_share_research_queue.csv`, `data/interim/a_share_company_profiles.csv`, and `data/interim/a_share_financial_indicators.csv`.

Generate dimensional A-share scores from fetched evidence:

```bash
python3 scripts/run_a_share_full_coverage_scoring.py
```

The scorer writes `data/processed/a_share_full_coverage_scores.csv` and `data/processed/a_share_full_coverage_watchlist.csv`. The full scores file keeps the complete audit fields, including `cyclicality_profile`, `compounding_profile`, `industry_outlook_*`, reasons, sources, and timestamps. The watchlist is a compact reading view with security code, security name, labeled score fields, peer group, peer-relative position, and scoring model version. Use `--require-complete` when the fetch queue is complete and the run should fail if any eligible A-share company remains unscored.

Fetch Hong Kong screening evidence into resumable interim CSV files:

```bash
python3 scripts/fetch_hong_kong_research_evidence.py
```

The fetcher writes `data/interim/hong_kong_research_queue.csv`, `data/interim/hong_kong_company_profiles.csv`, and `data/interim/hong_kong_financial_indicators.csv`. It uses Eastmoney HKF10 first and falls back to ETNet company information for newly listed securities that are not yet covered by Eastmoney.

Generate dimensional Hong Kong scores from fetched evidence:

```bash
python3 scripts/run_hong_kong_full_coverage_scoring.py
```

The scorer writes `data/processed/hong_kong_full_coverage_scores.csv` and `data/processed/hong_kong_full_coverage_watchlist.csv`. The full scores file keeps market identity and complete audit fields. The watchlist is a compact reading view with security code, security name, labeled score fields, peer group, peer-relative position, and scoring model version. When Hong Kong has duplicate currency counters for the same listed company, the full scores keep each security but the watchlist keeps one representative row.

Fetch U.S. screening evidence into resumable interim CSV files:

```bash
python3 scripts/fetch_us_research_evidence.py
```

The fetcher writes `data/interim/us_research_queue.csv`, `data/interim/us_company_profiles.csv`, and `data/interim/us_financial_indicators.csv`. It uses Nasdaq Trader for the raw security universe and SEC EDGAR `company_tickers`, `submissions`, and `companyfacts` for company profile and financial evidence. ETF, ETN, unit, warrant, right, preferred, closed-end fund, and other non-common-equity instruments are kept in the output with an explicit not-applicable status rather than being scored as listed companies. Use `--symbols UNH,MSFT` to refresh a targeted subset without rewriting unrelated evidence rows.

Generate dimensional U.S. scores from fetched evidence:

```bash
python3 scripts/run_us_full_coverage_scoring.py
```

The scorer writes `data/processed/us_full_coverage_scores.csv` and `data/processed/us_full_coverage_watchlist.csv`. The full scores file keeps market identity and complete audit fields. The watchlist is a compact reading view with security code, security name, labeled score fields, peer group, peer-relative position, and scoring model version. When the U.S. universe has multiple common-share classes for the same SEC CIK, the full scores keep each security but the watchlist keeps one representative row.
