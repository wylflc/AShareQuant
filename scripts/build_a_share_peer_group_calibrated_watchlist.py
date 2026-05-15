#!/usr/bin/env python3
"""Build the A-share watchlist from accepted peer-group decisions."""

from __future__ import annotations

import argparse
import csv
from collections import OrderedDict
from pathlib import Path


DEFAULT_DECISIONS_DIR = Path("data/processed")
DEFAULT_OUTPUT = Path("data/processed/a_share_peer_group_calibrated_watchlist.csv")

OUTPUT_COLUMNS = [
    "market_type",
    "market_label",
    "security_code",
    "security_name",
    "peer_groups",
    "decision_sources",
    "watch_selection_routes",
    "watch_reasons",
    "calibrated_standard_implications",
    "decided_at_utc",
    "source_decision_files",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions-dir", type=Path, default=DEFAULT_DECISIONS_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def read_decisions(decisions_dir: Path) -> list[tuple[Path, dict[str, str]]]:
    rows: list[tuple[Path, dict[str, str]]] = []
    for path in sorted(decisions_dir.glob("a_share_*_peer_group_decisions.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append((path, row))
    return rows


def coalesce_reason(row: dict[str, str]) -> str:
    return (
        row.get("analyst_response")
        or row.get("reviewer_reason")
        or row.get("reviewer_or_inferred_reason")
        or ""
    )


def infer_watch_selection_route(row: dict[str, str]) -> str:
    """Return how a watched company entered the calibrated watchlist."""
    explicit_route = row.get("watch_selection_route", "")
    if explicit_route:
        return explicit_route

    if row.get("reviewer_decision") != "watch":
        return ""

    decision_source = row.get("decision_source", "")
    if decision_source == "reviewer_explicit":
        return "direct_watch"
    if decision_source.startswith("analyst_"):
        return "boundary_judged_watch"

    reviewer_confidence = row.get("reviewer_confidence", "")
    if reviewer_confidence == "inferred_from_principle":
        return "boundary_judged_watch"
    if reviewer_confidence:
        return "direct_watch"

    prior_attention = row.get("prior_preliminary_attention", "")
    if prior_attention.startswith("watch_if") or prior_attention == "boundary_watch":
        return "boundary_judged_watch"
    return "direct_watch"


def build_watchlist(decision_rows: list[tuple[Path, dict[str, str]]]) -> list[dict[str, str]]:
    watchlist: OrderedDict[str, dict[str, list[str] | str]] = OrderedDict()

    for path, row in decision_rows:
        if row.get("reviewer_decision") != "watch":
            continue

        security_code = row["security_code"]
        entry = watchlist.setdefault(
            security_code,
            {
                "market_type": "A_SHARE",
                "market_label": "A股",
                "security_code": security_code,
                "security_name": row["security_name"],
                "peer_groups": [],
                "decision_sources": [],
                "watch_selection_routes": [],
                "watch_reasons": [],
                "calibrated_standard_implications": [],
                "decided_at_utc": row.get("decided_at_utc", ""),
                "source_decision_files": [],
            },
        )

        for column, value in [
            ("peer_groups", row.get("peer_group", "")),
            ("decision_sources", row.get("decision_source") or "reviewer_explicit_or_group_rule"),
            ("watch_selection_routes", infer_watch_selection_route(row)),
            ("watch_reasons", coalesce_reason(row)),
            ("calibrated_standard_implications", row.get("calibrated_standard_implication", "")),
            ("source_decision_files", str(path)),
        ]:
            values = entry[column]
            assert isinstance(values, list)
            if value and value not in values:
                values.append(value)

        decided_at = row.get("decided_at_utc", "")
        if decided_at > entry["decided_at_utc"]:
            entry["decided_at_utc"] = decided_at

    output_rows: list[dict[str, str]] = []
    for entry in watchlist.values():
        output_rows.append(
            {
                column: " | ".join(entry[column]) if isinstance(entry[column], list) else entry[column]
                for column in OUTPUT_COLUMNS
            }
        )
    return output_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    rows = build_watchlist(read_decisions(args.decisions_dir))
    write_csv(args.output, rows)
    print(f"wrote {len(rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
