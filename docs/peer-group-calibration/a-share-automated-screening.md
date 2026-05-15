# 1. A-Share Automated Peer-Group Screening Completion Pass

## 1.1 Purpose

This note documents the automated completion pass for A-share listed-company screening.

The pass exists because manually calibrated peer groups covered only part of the A-share universe. The user requested that all remaining unscreened A-share companies be screened automatically by industry group and committed without stopping for more reviewer calibration.

## 1.2 Input Boundary

The automated pass reads:

1. `data/processed/a_share_company_triage_reviews.csv`;
2. `data/processed/a_share_full_coverage_scores.csv`;
3. existing `data/processed/a_share_*_peer_group_decisions.csv` files.

Companies already covered by manual or semi-manual peer-group decisions are excluded from the automated pass. The output is a first-pass completion layer, not a replacement for future deep company reviews.

## 1.3 Rule

The pass uses conservative capability-first thresholds:

1. reject low-barrier groups by default when the business is easy to copy and has weak durable moat characteristics;
2. reject risk-warning names from automatic watchlist inclusion;
3. retain only the top-ranked companies in each peer group when moat, technology barrier, market position, business quality, and governance clear conservative thresholds;
4. cap the number of auto-retained companies per peer group so weaker copies do not flood the watchlist;
5. mark every automated watch entry as `boundary_judged_watch`.

The rule intentionally favors false negatives over false positives. A rejected company can still be challenged later and moved into a manual peer-group review.

## 1.4 Outputs

- `data/processed/a_share_automated_peer_group_decisions.csv`
- `data/processed/a_share_automated_peer_group_screening_summary.csv`
- Updated `data/processed/a_share_peer_group_calibrated_watchlist.csv`
- Updated `data/interim/a_share_peer_group_screening_queue.csv`

## 1.5 Limitations

This pass relies on the existing local evidence and scoring outputs. Those outputs are source-linked and auditable, but they are not equivalent to a full deep review based on annual reports and institutional research for every company.

The automated decisions should therefore be treated as first-pass screening coverage. Any company can be reopened if a later reviewer challenge identifies source-backed moat evidence that the automated pass missed.
