#!/usr/bin/env python3
"""Audit A-share workflow structure before peer-group calibration."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


DEFAULT_TRIAGE = Path("data/processed/a_share_company_triage_reviews.csv")
DEFAULT_QUEUE = Path("data/interim/a_share_deep_review_queue.csv")
DEFAULT_OUTPUT = Path("data/processed/a_share_review_standard_audit.csv")

AUDIT_COLUMNS = [
    "check_id",
    "check_area",
    "status",
    "market_type",
    "security_code",
    "security_name",
    "observed_value",
    "expected_value",
    "standard_risk",
    "next_action",
]

REVIEWER_CHALLENGE_CASES = [
    {
        "security_code": "600519",
        "security_name": "贵州茅台",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "300750",
        "security_name": "宁德时代",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "601899",
        "security_name": "紫金矿业",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "002594",
        "security_name": "比亚迪",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "603259",
        "security_name": "药明康德",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "688271",
        "security_name": "联影医疗",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "688617",
        "security_name": "惠泰医疗",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "601600",
        "security_name": "中国铝业",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "002428",
        "security_name": "云南锗业",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "600089",
        "security_name": "特变电工",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "600036",
        "security_name": "招商银行",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
    {
        "security_code": "002176",
        "security_name": "江特电机",
        "routing_expectation": "Reviewer-challenged company should enter deep review.",
        "workflow_risk": "A familiar company name should test routing only, not define the standard by itself.",
    },
]


class AuditError(RuntimeError):
    """Raised when audit inputs are missing or invalid."""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise AuditError(f"CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if not reader.fieldnames:
            raise AuditError(f"CSV has no header: {path}")
        return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_COLUMNS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def score_band(score: float) -> str:
    if score >= 85:
        return "85+"
    if score >= 80:
        return "80-84.99"
    if score >= 75:
        return "75-79.99"
    if score >= 70:
        return "70-74.99"
    if score >= 65:
        return "65-69.99"
    if score >= 60:
        return "60-64.99"
    return "<60"


def index_by_code(rows: list[dict[str, str]], code_column: str) -> dict[str, dict[str, str]]:
    return {row[code_column]: row for row in rows if row.get(code_column)}


def build_audit_rows(triage_rows: list[dict[str, str]], queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    audit_rows: list[dict[str, str]] = []
    if any(row.get("market_type") != "A_SHARE" for row in triage_rows + queue_rows):
        audit_rows.append(
            {
                "check_id": "market-scope",
                "check_area": "coverage",
                "status": "fail",
                "market_type": "A_SHARE",
                "observed_value": "non-A_SHARE rows present",
                "expected_value": "A_SHARE only",
                "standard_risk": "A-share calibration must not be mixed with Hong Kong or U.S. rows.",
                "next_action": "Regenerate with --markets A_SHARE before reviewing standards.",
            }
        )
    else:
        audit_rows.append(
            {
                "check_id": "market-scope",
                "check_area": "coverage",
                "status": "pass",
                "market_type": "A_SHARE",
                "observed_value": "A_SHARE only",
                "expected_value": "A_SHARE only",
                "standard_risk": "",
                "next_action": "Proceed with A-share-only peer-group calibration.",
            }
        )

    decisions = Counter(row["triage_decision"] for row in triage_rows)
    audit_rows.append(
        {
            "check_id": "triage-coverage",
            "check_area": "coverage",
            "status": "pass" if triage_rows else "fail",
            "market_type": "A_SHARE",
            "observed_value": f"{len(triage_rows)} triage rows; decisions={dict(decisions)}",
            "expected_value": "One company-level triage row for each eligible A-share listed company.",
            "standard_risk": "Missing rows would mean peer-group calibration is being drawn from a partial A-share universe.",
            "next_action": "Investigate raw-to-scored coverage if this count changes unexpectedly.",
        }
    )

    queue_decisions = Counter(row["triage_decision"] for row in queue_rows)
    audit_rows.append(
        {
            "check_id": "queue-coverage",
            "check_area": "coverage",
            "status": "pass" if queue_rows else "fail",
            "market_type": "A_SHARE",
            "observed_value": f"{len(queue_rows)} queue rows; decisions={dict(queue_decisions)}",
            "expected_value": "A-share deep-review queue from threshold, borderline, and reviewer-challenge triggers.",
            "standard_risk": "An empty or mixed queue would block A-share-first peer-group calibration.",
            "next_action": "Use the queue for deep reviews; do not treat it as the final watchlist.",
        }
    )

    audit_rows.append(
        {
            "check_id": "peer-group-calibration-required",
            "check_area": "calibration_method",
            "status": "observe",
            "market_type": "A_SHARE",
            "observed_value": "No reusable standard is frozen by this audit.",
            "expected_value": "Freeze standards only after comparing similar companies inside selected peer groups.",
            "standard_risk": "Randomly named familiar companies can bias the standard if treated as anchors.",
            "next_action": "Choose one A-share peer group, compare multiple companies, collect reviewer decisions, then document rules.",
        }
    )

    bands = Counter(score_band(float(row["triage_score"])) for row in triage_rows)
    for band in ["85+", "80-84.99", "75-79.99", "70-74.99", "65-69.99", "60-64.99", "<60"]:
        audit_rows.append(
            {
                "check_id": f"score-band-{band}",
                "check_area": "distribution",
                "status": "observe",
                "market_type": "A_SHARE",
                "observed_value": str(bands[band]),
                "expected_value": "For reviewer inspection; not a fixed quota.",
                "standard_risk": "Distribution drift can reveal an over-loose or over-tight triage standard.",
                "next_action": "Use the distribution to select peer groups; do not impose a fixed candidate quota.",
            }
        )

    triage_by_code = index_by_code(triage_rows, "representative_security_code")
    queue_by_code = index_by_code(queue_rows, "representative_security_code")
    for case in REVIEWER_CHALLENGE_CASES:
        code = case["security_code"]
        triage = triage_by_code.get(code)
        queue = queue_by_code.get(code)
        if not triage:
            status = "fail"
            observed = "missing from triage"
            next_action = "Investigate company identity mapping or scorer coverage."
        elif not queue:
            status = "fail"
            observed = f"triage_score={triage['triage_score']}; decision={triage['triage_decision']}; not queued"
            next_action = "Fix reviewer-challenge routing before peer-group calibration proceeds."
        else:
            status = "pass"
            observed = (
                f"queue_rank={queue['queue_rank']}; triage_score={queue['triage_score']}; "
                f"decision={queue['triage_decision']}; trigger={queue['deep_review_trigger']}"
            )
            next_action = "Treat as routing-only; use it in calibration only if it belongs to the selected peer group."
        audit_rows.append(
            {
                "check_id": f"reviewer-challenge-routing-{code}",
                "check_area": "reviewer_challenge_routing",
                "status": status,
                "market_type": "A_SHARE",
                "security_code": code,
                "security_name": case["security_name"],
                "observed_value": observed,
                "expected_value": case["routing_expectation"],
                "standard_risk": case["workflow_risk"],
                "next_action": next_action,
            }
        )
    return audit_rows


def run(args: argparse.Namespace) -> int:
    triage_rows = read_csv(args.triage)
    queue_rows = read_csv(args.queue)
    audit_rows = build_audit_rows(triage_rows, queue_rows)
    write_csv(args.output, audit_rows)
    failed = sum(1 for row in audit_rows if row["status"] == "fail")
    print(f"Wrote {len(audit_rows)} A-share standard audit rows to {args.output}")
    print(f"Failed checks: {failed}")
    return 1 if failed else 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit A-share workflow structure before peer-group calibration.")
    parser.add_argument("--triage", type=Path, default=DEFAULT_TRIAGE)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
