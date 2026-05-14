# Use full-coverage dimensional moat scoring

## Status

Accepted

## Context

The previous screening workflow could treat a missing local evidence row as `insufficient_evidence`. That made the candidate count depend on how many companies had already been manually reviewed, not on the underlying quality of the A-share or Hong Kong universe.

For the A-share and Hong Kong universes, the desired workflow is different: every eligible listed company should receive the same business-quality analysis and a score. Evidence insufficiency is a narrow company-level condition, not a workflow shortcut.

The scoring model also needs to be auditable. A single blended score is not enough because future reviewers need to see whether the result came from business moat, technical barrier, market position, operating quality, or risk judgment.

## Decision

Use a full-coverage screening workflow for `data/raw/a_share_securities.csv` and `data/raw/hong_kong_securities.csv`.

Every eligible A-share or Hong Kong listed company must receive dimensional scores for:

1. Business moat and capital-replication resistance.
2. Technology, product, process, or supply-chain barrier.
3. Market position and competitive structure.
4. Business model quality.
5. Operating and financial quality.
6. Governance, disclosure, and risk quality.

The final score is a weighted total computed from the recorded dimension scores. The processed CSV must keep each dimension score, level, and reason so the final score is traceable.

Apply the capital replicability test across dimensions: ask whether a well-funded new entrant could quickly compete with and overtake the company mainly through capital spending. The answer should influence the relevant dimension scores.

Use `insufficient_disclosure` only when the company is newly listed, has not disclosed enough periodic reports, and lacks authoritative public business descriptions from filings, official materials, credible media, or reputable research institutions.

## Consequences

- Candidate count will no longer be a proxy for manual evidence coverage.
- The screening workflow must maintain research queues and validation steps to ensure full A-share and Hong Kong coverage.
- Processed outputs will contain more columns because they must preserve dimensional scores and reasons.
- Research can be batched operationally, but a full-coverage run is incomplete until every eligible A-share or Hong Kong company has a score or the narrow `insufficient_disclosure` status.
- Missing local evidence is a workflow gap and should fail full-coverage validation rather than exclude the company.

## Alternatives Considered

- Keep candidate-only screening from manually entered evidence rows. Rejected because it makes the watchlist depend on research order and undercounts companies that have not yet been reviewed.
- Use a single 0-100 score with one reason. Rejected because it hides the difference between brand moat, technical moat, business model quality, and operating risk.
- Treat all missing evidence as insufficient evidence. Rejected because most public listed companies have filings and other public information that are sufficient for first-pass analysis.
