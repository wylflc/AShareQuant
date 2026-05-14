#!/usr/bin/env python3
"""Build two-layer company review triage and deep-review queue outputs."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_A_SHARE_SCORES = Path("data/processed/a_share_full_coverage_scores.csv")
DEFAULT_HONG_KONG_SCORES = Path("data/processed/hong_kong_full_coverage_scores.csv")
DEFAULT_US_SCORES = Path("data/processed/us_full_coverage_scores.csv")
DEFAULT_CHALLENGES = Path("data/interim/deep_review_challenges.csv")
DEFAULT_TRIAGE_OUTPUT = Path("data/processed/company_triage_reviews.csv")
DEFAULT_QUEUE_OUTPUT = Path("data/interim/deep_review_queue.csv")
MARKET_SCORE_PATHS = {
    "A_SHARE": DEFAULT_A_SHARE_SCORES,
    "HONG_KONG": DEFAULT_HONG_KONG_SCORES,
    "USA": DEFAULT_US_SCORES,
}

TRIAGE_COLUMNS = [
    "market_type",
    "market_label",
    "company_key",
    "representative_security_code",
    "security_codes",
    "listed_company_name",
    "security_name",
    "exchange",
    "currency",
    "industry",
    "peer_group",
    "triage_score",
    "triage_decision",
    "deep_review_required",
    "deep_review_trigger",
    "challenge_reason",
    "business_moat_score",
    "technology_barrier_score",
    "market_position_score",
    "business_quality_score",
    "operating_quality_score",
    "industry_outlook_score",
    "governance_risk_score",
    "cyclicality_profile",
    "compounding_profile",
    "triage_reason",
    "source_scoring_model_version",
    "source_score_urls",
    "triaged_at_utc",
]

QUEUE_COLUMNS = [
    "queue_rank",
    "market_type",
    "market_label",
    "company_key",
    "representative_security_code",
    "security_name",
    "listed_company_name",
    "triage_score",
    "triage_decision",
    "deep_review_trigger",
    "challenge_reason",
    "priority",
    "review_status",
    "required_source_standard",
    "next_action",
    "source_scoring_model_version",
    "queued_at_utc",
]


class ReviewError(RuntimeError):
    """Raised when two-layer review inputs are invalid."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise ReviewError(f"CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if not reader.fieldnames:
            raise ReviewError(f"CSV has no header: {path}")
        return list(reader.fieldnames), rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def number(raw: str | None) -> float | None:
    if raw in (None, "", "--"):
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def score_text(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def load_challenges(path: Path) -> dict[tuple[str, str], str]:
    if not path.exists():
        return {}
    _, rows = read_csv(path)
    challenges: dict[tuple[str, str], str] = {}
    for row in rows:
        market_type = row.get("market_type", "").strip()
        security_code = row.get("security_code", "").strip()
        company_key = row.get("company_key", "").strip()
        reason = row.get("challenge_reason", "").strip()
        if market_type and security_code:
            challenges[(market_type, security_code)] = reason
        if market_type and company_key:
            challenges[(market_type, company_key)] = reason
    return challenges


def market_defaults(path: Path, row: dict[str, str]) -> tuple[str, str]:
    if row.get("market_type"):
        return row["market_type"], row.get("market_label", "")
    if "a_share" in path.name:
        return "A_SHARE", "A股"
    return "", ""


def company_key(market_type: str, row: dict[str, str]) -> str:
    if market_type == "HONG_KONG":
        identity = row.get("isin") or row.get("listed_company_name") or row["security_code"]
    elif market_type == "USA":
        identity = row.get("sec_cik") or row.get("listed_company_name") or row["security_code"]
    else:
        identity = row.get("listed_company_name") or row["security_code"]
    return f"{market_type}:{identity}"


def load_scored_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        _, source_rows = read_csv(path)
        for row in source_rows:
            if row.get("screening_status") != "scored":
                continue
            score = number(row.get("weighted_total_score"))
            if score is None:
                continue
            market_type, market_label = market_defaults(path, row)
            if not market_type:
                continue
            copied = dict(row)
            copied["_market_type"] = market_type
            copied["_market_label"] = market_label
            copied["_company_key"] = company_key(market_type, row)
            copied["_score"] = score
            rows.append(copied)
    return rows


def score_paths_for_markets(args: argparse.Namespace) -> list[Path]:
    overrides = {
        "A_SHARE": args.a_share_scores,
        "HONG_KONG": args.hong_kong_scores,
        "USA": args.us_scores,
    }
    return [overrides[market] for market in args.markets]


def representative_sort_key(row: dict[str, str]) -> tuple[float, int, str]:
    currency = row.get("currency", "")
    currency_rank = 0 if currency in ("", "CNY", "HKD", "USD") else 1
    return (-row["_score"], currency_rank, row["security_code"])


def group_company_rows(rows: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["_company_key"], []).append(row)
    return [sorted(items, key=representative_sort_key) for items in grouped.values()]


def triage_decision(score: float, challenged: bool, threshold: float, borderline_low: float) -> str:
    if challenged:
        return "challenged"
    if score >= threshold:
        return "advance_to_deep_review"
    if score >= borderline_low:
        return "borderline"
    return "reject"


def deep_review_trigger(decision: str, score: float, challenged: bool, threshold: float) -> str:
    triggers: list[str] = []
    if score >= threshold:
        triggers.append(f"triage_score>={threshold:g}")
    if decision == "borderline":
        triggers.append("borderline")
    if challenged:
        triggers.append("manual_challenge")
    return ";".join(triggers)


def priority(decision: str, score: float, challenged: bool) -> int:
    if challenged:
        return 0
    if score >= 75:
        return 1
    if score >= 70:
        return 2
    if score >= 65:
        return 3
    if decision == "borderline":
        return 4
    return 9


def source_urls(row: dict[str, str]) -> str:
    return row.get("source_urls", "")


def build_triage_rows(
    groups: list[list[dict[str, str]]],
    challenges: dict[tuple[str, str], str],
    threshold: float,
    borderline_low: float,
    triaged_at: str,
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for group in groups:
        row = group[0]
        market_type = row["_market_type"]
        company_key_value = row["_company_key"]
        challenge_reason = (
            challenges.get((market_type, row["security_code"]))
            or challenges.get((market_type, company_key_value))
            or ""
        )
        challenged = bool(challenge_reason)
        score = float(row["_score"])
        decision = triage_decision(score, challenged, threshold, borderline_low)
        trigger = deep_review_trigger(decision, score, challenged, threshold)
        required = bool(trigger)
        if decision == "challenged":
            reason = "Manual challenge overrides the baseline triage score and routes the company to deep review."
        elif decision == "advance_to_deep_review":
            reason = "Baseline triage score meets the agreed deep-review entry threshold."
        elif decision == "borderline":
            reason = "Baseline triage score is close enough to require second-layer verification."
        else:
            reason = "Baseline triage score is below the deep-review threshold and no manual challenge is recorded."
        output.append(
            {
                "market_type": market_type,
                "market_label": row["_market_label"],
                "company_key": company_key_value,
                "representative_security_code": row["security_code"],
                "security_codes": ";".join(item["security_code"] for item in group),
                "listed_company_name": row.get("listed_company_name", ""),
                "security_name": row.get("security_name", ""),
                "exchange": row.get("exchange", ""),
                "currency": row.get("currency", ""),
                "industry": row.get("industry", ""),
                "peer_group": row.get("peer_group", ""),
                "triage_score": score_text(score),
                "triage_decision": decision,
                "deep_review_required": "true" if required else "false",
                "deep_review_trigger": trigger,
                "challenge_reason": challenge_reason,
                "business_moat_score": row.get("business_moat_score", ""),
                "technology_barrier_score": row.get("technology_barrier_score", ""),
                "market_position_score": row.get("market_position_score", ""),
                "business_quality_score": row.get("business_quality_score", ""),
                "operating_quality_score": row.get("operating_quality_score", ""),
                "industry_outlook_score": row.get("industry_outlook_score", ""),
                "governance_risk_score": row.get("governance_risk_score", ""),
                "cyclicality_profile": row.get("cyclicality_profile", ""),
                "compounding_profile": row.get("compounding_profile", ""),
                "triage_reason": reason,
                "source_scoring_model_version": row.get("scoring_model_version", ""),
                "source_score_urls": source_urls(row),
                "triaged_at_utc": triaged_at,
            }
        )
    output.sort(key=lambda item: (-float(item["triage_score"]), item["market_type"], item["representative_security_code"]))
    return output


def build_queue_rows(triage_rows: list[dict[str, str]], queued_at: str) -> list[dict[str, str]]:
    rows = [row for row in triage_rows if row["deep_review_required"] == "true"]
    rows.sort(
        key=lambda row: (
            priority(row["triage_decision"], float(row["triage_score"]), "manual_challenge" in row["deep_review_trigger"]),
            -float(row["triage_score"]),
            row["market_type"],
            row["representative_security_code"],
        )
    )
    output: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        required_source_standard = (
            "Use company periodic reports, exchange announcements, regulator disclosures, official IR materials, "
            "reputable institution reports, or professional research reports; aggregator profiles are discovery hints only."
        )
        output.append(
            {
                "queue_rank": str(index),
                "market_type": row["market_type"],
                "market_label": row["market_label"],
                "company_key": row["company_key"],
                "representative_security_code": row["representative_security_code"],
                "security_name": row["security_name"],
                "listed_company_name": row["listed_company_name"],
                "triage_score": row["triage_score"],
                "triage_decision": row["triage_decision"],
                "deep_review_trigger": row["deep_review_trigger"],
                "challenge_reason": row["challenge_reason"],
                "priority": str(priority(row["triage_decision"], float(row["triage_score"]), "manual_challenge" in row["deep_review_trigger"])),
                "review_status": "pending",
                "required_source_standard": required_source_standard,
                "next_action": "Collect authoritative sources and complete a deep company review with common and special dimensions.",
                "source_scoring_model_version": row["source_scoring_model_version"],
                "queued_at_utc": queued_at,
            }
        )
    return output


def run(args: argparse.Namespace) -> tuple[int, int]:
    paths = score_paths_for_markets(args)
    challenges = load_challenges(args.challenges)
    scored_rows = load_scored_rows(paths)
    groups = group_company_rows(scored_rows)
    timestamp = utc_now()
    triage_rows = build_triage_rows(groups, challenges, args.triage_threshold, args.borderline_low, timestamp)
    queue_rows = build_queue_rows(triage_rows, timestamp)
    write_csv(args.triage_output, TRIAGE_COLUMNS, triage_rows)
    write_csv(args.queue_output, QUEUE_COLUMNS, queue_rows)
    return len(triage_rows), len(queue_rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build two-layer company review triage outputs.")
    parser.add_argument(
        "--markets",
        nargs="+",
        choices=sorted(MARKET_SCORE_PATHS),
        default=sorted(MARKET_SCORE_PATHS),
        help="Markets to include in this run. Use one market while calibrating before cross-market rollout.",
    )
    parser.add_argument("--a-share-scores", type=Path, default=DEFAULT_A_SHARE_SCORES)
    parser.add_argument("--hong-kong-scores", type=Path, default=DEFAULT_HONG_KONG_SCORES)
    parser.add_argument("--us-scores", type=Path, default=DEFAULT_US_SCORES)
    parser.add_argument("--challenges", type=Path, default=DEFAULT_CHALLENGES)
    parser.add_argument("--triage-output", type=Path, default=DEFAULT_TRIAGE_OUTPUT)
    parser.add_argument("--queue-output", type=Path, default=DEFAULT_QUEUE_OUTPUT)
    parser.add_argument("--triage-threshold", type=float, default=65.0)
    parser.add_argument("--borderline-low", type=float, default=60.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    triage_count, queue_count = run(args)
    print(f"Wrote {triage_count} company triage rows to {args.triage_output}")
    print(f"Wrote {queue_count} deep-review queue rows to {args.queue_output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReviewError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
