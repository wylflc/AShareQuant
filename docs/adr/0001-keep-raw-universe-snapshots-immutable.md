# Keep raw universe snapshots immutable

Raw universe CSV files in `data/raw/` remain provider snapshots and are not edited with screening scores, even when a downstream workflow needs per-security decisions. Screening outputs live in `data/processed/` and reference evidence in `data/interim/` so raw provenance stays auditable and derived moat scores can be regenerated or revised without mutating source captures.
