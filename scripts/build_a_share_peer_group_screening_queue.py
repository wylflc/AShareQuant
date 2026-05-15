#!/usr/bin/env python3
"""Build the next A-share peer-group screening queue.

The queue is a coverage-control artifact. It does not decide whether a company
enters the watchlist; it shows which peer groups still need reviewer-calibrated
screening and which groups may be suitable for whole-group low-barrier rejection.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean


DEFAULT_TRIAGE = Path("data/processed/a_share_company_triage_reviews.csv")
DEFAULT_DECISIONS_DIR = Path("data/processed")
DEFAULT_OUTPUT = Path("data/interim/a_share_peer_group_screening_queue.csv")

OUTPUT_COLUMNS = [
    "priority_rank",
    "market_type",
    "peer_group",
    "screening_status",
    "recommended_review_mode",
    "total_company_count",
    "decided_security_count",
    "decided_watch_count",
    "unreviewed_company_count",
    "deep_review_candidate_count",
    "advance_to_deep_review_count",
    "borderline_count",
    "triage_reject_count",
    "challenged_count",
    "max_triage_score",
    "average_triage_score",
    "top_unreviewed_examples",
]

LOW_BARRIER_KEYWORDS = [
    "餐饮",
    "百货",
    "超市",
    "连锁",
    "贸易",
    "一般物业经营",
    "装修装饰",
    "建筑装饰设计",
    "旅游服务",
]

UNCLEAR_PEER_GROUP_KEYWORDS = ["综合", "其他", "其它"]


@dataclass
class GroupSummary:
    peer_group: str
    rows: list[dict[str, str]] = field(default_factory=list)
    unreviewed_rows: list[dict[str, str]] = field(default_factory=list)
    decided_codes: set[str] = field(default_factory=set)
    watch_codes: set[str] = field(default_factory=set)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--triage", type=Path, default=DEFAULT_TRIAGE)
    parser.add_argument("--decisions-dir", type=Path, default=DEFAULT_DECISIONS_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def read_decisions(decisions_dir: Path) -> tuple[set[str], set[str]]:
    decided_codes: set[str] = set()
    watch_codes: set[str] = set()
    for path in sorted(decisions_dir.glob("a_share_*_peer_group_decisions.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                code = row.get("security_code", "")
                if not code:
                    continue
                decided_codes.add(code)
                if row.get("reviewer_decision") == "watch":
                    watch_codes.add(code)
    return decided_codes, watch_codes


def read_triage(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def representative_code(row: dict[str, str]) -> str:
    return row.get("representative_security_code") or row.get("security_code", "")


def triage_score(row: dict[str, str]) -> float:
    try:
        return float(row.get("triage_score", "") or 0.0)
    except ValueError:
        return 0.0


def is_deep_candidate(row: dict[str, str]) -> bool:
    return row.get("deep_review_required") == "true" or row.get("triage_decision") in {
        "advance_to_deep_review",
        "borderline",
        "challenged",
    }


def recommended_review_mode(peer_group: str, unreviewed_rows: list[dict[str, str]]) -> str:
    if not unreviewed_rows:
        return "no_action"
    if any(keyword in peer_group for keyword in LOW_BARRIER_KEYWORDS):
        return "low_barrier_group_rejection_review"
    if any(keyword in peer_group for keyword in UNCLEAR_PEER_GROUP_KEYWORDS):
        return "ask_reviewer_before_decision"
    if any(is_deep_candidate(row) for row in unreviewed_rows):
        return "peer_group_calibration"
    return "batch_reject_with_spot_check"


def screening_status(summary: GroupSummary) -> str:
    if not summary.unreviewed_rows:
        return "complete"
    if summary.decided_codes:
        return "partially_screened"
    return "not_started"


def top_examples(rows: list[dict[str, str]], limit: int = 5) -> str:
    ranked = sorted(rows, key=triage_score, reverse=True)[:limit]
    return " | ".join(
        ":".join(
            [
                representative_code(row),
                row.get("security_name", ""),
                f"{triage_score(row):.2f}",
                row.get("triage_decision", ""),
            ]
        )
        for row in ranked
    )


def summarize(
    triage_rows: list[dict[str, str]], decided_codes: set[str], watch_codes: set[str]
) -> list[dict[str, str]]:
    summaries: dict[str, GroupSummary] = {}
    for row in triage_rows:
        peer_group = row.get("peer_group") or "UNKNOWN"
        summary = summaries.setdefault(peer_group, GroupSummary(peer_group=peer_group))
        summary.rows.append(row)

        code = representative_code(row)
        if code in decided_codes:
            summary.decided_codes.add(code)
            if code in watch_codes:
                summary.watch_codes.add(code)
        else:
            summary.unreviewed_rows.append(row)

    output_rows: list[dict[str, str]] = []
    for summary in summaries.values():
        unreviewed = summary.unreviewed_rows
        triage_counts = Counter(row.get("triage_decision", "") for row in unreviewed)
        scores = [triage_score(row) for row in unreviewed]
        output_rows.append(
            {
                "priority_rank": "",
                "market_type": "A_SHARE",
                "peer_group": summary.peer_group,
                "screening_status": screening_status(summary),
                "recommended_review_mode": recommended_review_mode(summary.peer_group, unreviewed),
                "total_company_count": str(len(summary.rows)),
                "decided_security_count": str(len(summary.decided_codes)),
                "decided_watch_count": str(len(summary.watch_codes)),
                "unreviewed_company_count": str(len(unreviewed)),
                "deep_review_candidate_count": str(sum(1 for row in unreviewed if is_deep_candidate(row))),
                "advance_to_deep_review_count": str(triage_counts["advance_to_deep_review"]),
                "borderline_count": str(triage_counts["borderline"]),
                "triage_reject_count": str(triage_counts["reject"]),
                "challenged_count": str(triage_counts["challenged"]),
                "max_triage_score": f"{max(scores):.2f}" if scores else "",
                "average_triage_score": f"{mean(scores):.2f}" if scores else "",
                "top_unreviewed_examples": top_examples(unreviewed),
            }
        )

    output_rows.sort(
        key=lambda row: (
            row["screening_status"] == "complete",
            row["recommended_review_mode"] == "batch_reject_with_spot_check",
            -int(row["deep_review_candidate_count"] or 0),
            -float(row["max_triage_score"] or 0),
            -int(row["unreviewed_company_count"] or 0),
            row["peer_group"],
        )
    )
    for rank, row in enumerate(output_rows, start=1):
        row["priority_rank"] = str(rank)
    return output_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    decided_codes, watch_codes = read_decisions(args.decisions_dir)
    rows = summarize(read_triage(args.triage), decided_codes, watch_codes)
    write_csv(args.output, rows)
    print(f"wrote {len(rows)} peer groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
