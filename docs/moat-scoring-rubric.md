# Moat Scoring Rubric

## 1. Purpose

This rubric defines the full-coverage business-quality screening standard for listed companies in the A-share, Hong Kong, and U.S. universes. It is not a valuation model and does not produce buy recommendations.

The goal is to score the real competitive strength of each listed company using comparable dimensions, reliable public evidence, and explicit reasoning.

## 2. Scope

The full-coverage runs apply to every eligible listed company or listed security represented in `data/raw/a_share_securities.csv`, `data/raw/hong_kong_securities.csv`, and `data/raw/us_securities.csv`.

For the U.S. universe, raw Nasdaq Trader data contains many non-company or non-common-equity instruments. ETF, ETN, unit, warrant, right, preferred, closed-end fund, and similar instruments should remain in the processed output with a not-applicable screening status, but they should not receive listed-company moat scores.

The raw universe remains immutable. Research queues, evidence summaries, dimensional scores, and derived watchlists belong in `data/interim/` and `data/processed/`.

## 3. Evidence Standard

Each company should be scored from reliable public evidence, including annual reports, quarterly reports, exchange filings, official investor-relations materials, regulator disclosures, credible media, industry association data, and reputable research institutions.

`insufficient_disclosure` is allowed only when all conditions hold:

1. The company has been listed for less than 12 months.
2. The company has not disclosed at least one annual report after listing.
3. Public filings, official materials, credible media, and reputable research institutions do not provide enough business description to support the rubric.

Missing local evidence rows, unsearched companies, or incomplete manual review are workflow states. They are not evidence insufficiency.

## 4. Capital Replicability Test

Every dimension should ask whether a well-funded new entrant could quickly win mainly by spending money.

High scores require evidence that capital alone is not enough because the company has hard-to-replicate advantages such as brand trust, customer relationships, licenses, regulated assets, scarce resources, proprietary technology, manufacturing know-how, supply-chain control, data network effects, ecosystem lock-in, or long clinical and quality-validation cycles.

Low scores indicate that a funded competitor could plausibly build similar capacity, hire similar teams, acquire traffic, open comparable outlets, copy products, or win customers without a long accumulation period.

## 5. Weighted Dimensions

Each dimension is scored from 0 to 100. The final score is the weighted sum rounded to the nearest integer.

| Dimension | Weight | Required CSV columns |
| --- | ---: | --- |
| Business moat and capital-replication resistance | 25% | `business_moat_score`, `business_moat_level`, `business_moat_reason` |
| Technology, product, process, or supply-chain barrier | 20% | `technology_barrier_score`, `technology_barrier_level`, `technology_barrier_reason` |
| Market position and competitive structure | 15% | `market_position_score`, `market_position_level`, `market_position_reason` |
| Business model quality | 15% | `business_quality_score`, `business_quality_level`, `business_quality_reason` |
| Operating and financial quality | 15% | `operating_quality_score`, `operating_quality_level`, `operating_quality_reason` |
| Governance, disclosure, and risk quality | 10% | `governance_risk_score`, `governance_risk_level`, `governance_risk_reason` |

## 6. Dimension Bands

Use the same score bands for every dimension.

| Band | Score | Meaning |
| --- | ---: | --- |
| S | 90-100 | Elite. A well-funded entrant cannot realistically replicate or overtake the company in a short period. |
| A | 80-89 | Strong. Capital helps competitors but important bottlenecks remain hard to buy quickly. |
| B | 70-79 | Clear advantage. The company has visible strengths, but determined competitors can narrow the gap over time. |
| C | 55-69 | Moderate. The company is viable, but a funded entrant with good execution could challenge it. |
| D | 40-54 | Weak. Advantages are limited and mostly replicable through capital, hiring, distribution, or normal execution. |
| E | 0-39 | Fragile. The company has little durable advantage or has severe operating, governance, or survival risk. |

## 7. Dimension Guidance

### 7.1 Business Moat And Capital-Replication Resistance

Score brands, channels, licenses, scarce assets, customer lock-in, network effects, switching costs, ecosystem control, and accumulated trust.

The core question is: if a new player had enough capital, could it enter this industry and beat this company mainly by spending money?

### 7.2 Technology, Product, Process, Or Supply-Chain Barrier

Score proprietary technology, patents, manufacturing process depth, product complexity, quality systems, engineering culture, data assets, supplier control, certification barriers, and time-to-scale.

The core question is: can a new player buy equipment and talent and quickly match the company's technical or operational capability, or are there learning curves and ecosystem constraints that capital cannot compress?

### 7.3 Market Position And Competitive Structure

Score market share, rank, bargaining power, customer diversification, industry concentration, regulatory position, and ability to shape the category.

The core question is: does the company have an entrenched position in an attractive structure, or is it one of many interchangeable competitors?

### 7.4 Business Model Quality

Score recurring demand, pricing power, customer retention, unit economics, cyclicality, product mix, revenue durability, and dependence on subsidies or one-off project demand.

The core question is: can the company keep earning attractive business returns without constantly buying growth?

### 7.5 Operating And Financial Quality

Score cash conversion, margin profile, ROE or ROIC quality, balance-sheet pressure, working-capital discipline, capital intensity, earnings stability, and resilience through downturns.

The core question is: does the operating record support the claimed competitive strength, or does the business require heavy capital and favorable cycles to look good?

### 7.6 Governance, Disclosure, And Risk Quality

Score governance quality, related-party risk, accounting transparency, regulatory exposure, safety or environmental risk, geopolitical risk, customer concentration, and disclosure reliability.

The core question is: can investors trust the public record enough to compare this company fairly, and are there structural risks that undermine otherwise strong business qualities?

## 8. Relative Peer Judgment

Each company should include `peer_group` and `peer_relative_position` using one of:

- `stronger_than_peers`
- `above_average`
- `average`
- `below_average`
- `weak`
- `hard_to_distinguish`

The peer comparison should use comparable listed companies or clear industry peers. When peers are hard to identify, record the reason rather than silently skipping the comparison.

## 9. Required Output Fields

The full-coverage processed CSV should preserve source security identifiers and add:

- `screening_status`
- `disclosure_status`
- `peer_group`
- `peer_relative_position`
- one score, level, and reason column for each weighted dimension
- `weighted_total_score`
- `overall_level`
- `overall_reason`
- `evidence_confidence`
- `source_urls`
- `reviewed_at_utc`
- `scoring_model_version`

## 10. Execution Plan

1. Remove tracked local skill files from Git and keep `.agents/` ignored.
2. Generate full A-share, Hong Kong, and U.S. research queues from the raw universes.
3. Collect source evidence for each listed company by filings, official materials, and authoritative external descriptions.
4. Normalize each company into a peer group.
5. Assign every dimensional score with a reason and sources.
6. Compute the weighted total from stored dimension scores.
7. Validate that every eligible raw A-share, Hong Kong, and U.S. row has either full dimensional scores or the narrow `insufficient_disclosure` status; U.S. non-company/non-common-equity instruments must have an explicit not-applicable status.
8. Generate processed full-coverage outputs and a watchlist candidate view.
