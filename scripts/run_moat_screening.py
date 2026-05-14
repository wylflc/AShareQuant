#!/usr/bin/env python3
"""Run evidence-backed first-pass moat screening for A-share and Hong Kong securities.

The script does not invent scores. A security receives a moat score only when
`data/interim/moat_screening_evidence.csv` contains a source-backed evidence row
with a numeric score and reason. Missing evidence is recorded explicitly as an
exclusion reason so the screening output remains auditable.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_A_SHARE_RAW = Path("data/raw/a_share_securities.csv")
DEFAULT_HONG_KONG_RAW = Path("data/raw/hong_kong_securities.csv")
DEFAULT_EVIDENCE = Path("data/interim/moat_screening_evidence.csv")
DEFAULT_A_SHARE_OUTPUT = Path("data/processed/a_share_securities_screened.csv")
DEFAULT_HONG_KONG_OUTPUT = Path("data/processed/hong_kong_securities_screened.csv")
DEFAULT_CANDIDATES_OUTPUT = Path("data/processed/moat_watchlist_candidates.csv")

SCREENING_COLUMNS = [
    "market_type",
    "market_label",
    "moat_score",
    "screening_decision",
    "screening_reason",
    "evidence_sources",
    "screening_run_at_utc",
]

CANDIDATE_COLUMNS = [
    "market_type",
    "market_label",
    "security_code",
    "symbol",
    "exchange",
    "board",
    "listed_company_name",
    "security_name",
    "currency",
    "moat_score",
    "screening_reason",
    "evidence_sources",
    "screening_run_at_utc",
    "source_raw_file",
]

EVIDENCE_COLUMNS = [
    "market_type",
    "security_code",
    "listed_company_name",
    "source_urls",
    "business_summary",
    "moat_summary",
    "technology_barrier_summary",
    "cash_flow_quality_summary",
    "margin_quality_summary",
    "market_position_summary",
    "risks",
    "score_0_100",
    "score_reason",
    "evidence_retrieved_at_utc",
]


class ScreeningError(RuntimeError):
    """Raised when screening inputs are invalid."""


@dataclass(frozen=True)
class MarketConfig:
    market_type: str
    market_label: str
    raw_path: Path
    output_path: Path


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise ScreeningError(f"Input CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if not reader.fieldnames:
            raise ScreeningError(f"Input CSV has no header: {path}")
        return list(reader.fieldnames), rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def ensure_evidence_template(path: Path) -> None:
    if path.exists():
        return
    write_csv(path, EVIDENCE_COLUMNS, [])


def load_evidence(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    ensure_evidence_template(path)
    fieldnames, rows = read_csv(path)
    missing = [column for column in EVIDENCE_COLUMNS if column not in fieldnames]
    if missing:
        raise ScreeningError(f"Evidence CSV missing columns: {', '.join(missing)}")

    evidence: dict[tuple[str, str], dict[str, str]] = {}
    duplicates: list[str] = []
    for row in rows:
        market_type = row["market_type"].strip().upper()
        security_code = row["security_code"].strip()
        if not market_type and not security_code:
            continue
        key = (market_type, security_code)
        if key in evidence:
            duplicates.append("/".join(key))
        evidence[key] = row | {"market_type": market_type, "security_code": security_code}
    if duplicates:
        raise ScreeningError(f"Duplicate evidence rows: {', '.join(duplicates[:10])}")
    return evidence


def score_from_evidence(row: dict[str, str]) -> int | None:
    raw_score = row["score_0_100"].strip()
    if raw_score == "":
        return None
    try:
        score = int(raw_score)
    except ValueError as exc:
        raise ScreeningError(f"Invalid score_0_100 for {row['market_type']}/{row['security_code']}: {raw_score}") from exc
    if score < 0 or score > 100:
        raise ScreeningError(f"score_0_100 out of range for {row['market_type']}/{row['security_code']}: {score}")
    return score


def validate_scored_evidence(row: dict[str, str], score: int) -> None:
    if not row["source_urls"].strip():
        raise ScreeningError(f"Scored evidence missing source_urls for {row['market_type']}/{row['security_code']}")
    if not row["score_reason"].strip():
        raise ScreeningError(f"Scored evidence missing score_reason for {row['market_type']}/{row['security_code']}")
    for url in [part.strip() for part in row["source_urls"].split(";") if part.strip()]:
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ScreeningError(f"Evidence source is not a URL for {row['market_type']}/{row['security_code']}: {url}")
    if score >= 70 and not row["moat_summary"].strip():
        raise ScreeningError(f"Candidate evidence missing moat_summary for {row['market_type']}/{row['security_code']}")


def screen_security(
    security: dict[str, str],
    market: MarketConfig,
    evidence: dict[tuple[str, str], dict[str, str]],
    candidate_threshold: int,
    run_at_utc: str,
) -> dict[str, str]:
    security_code = security["security_code"].strip()
    evidence_row = evidence.get((market.market_type, security_code))

    result = dict(security)
    result.update(
        {
            "market_type": market.market_type,
            "market_label": market.market_label,
            "moat_score": "",
            "screening_decision": "excluded",
            "screening_reason": "insufficient_evidence: no reliable source-backed evidence row; not scored to avoid fabrication",
            "evidence_sources": "",
            "screening_run_at_utc": run_at_utc,
        }
    )

    if evidence_row is None:
        return result

    score = score_from_evidence(evidence_row)
    source_urls = evidence_row["source_urls"].strip()
    score_reason = evidence_row["score_reason"].strip()

    if score is None:
        result["screening_reason"] = score_reason or "insufficient_evidence: evidence row has no numeric score"
        result["evidence_sources"] = source_urls
        return result

    validate_scored_evidence(evidence_row, score)
    result["moat_score"] = str(score)
    result["evidence_sources"] = source_urls
    if score >= candidate_threshold:
        result["screening_decision"] = "candidate"
        result["screening_reason"] = score_reason
    else:
        result["screening_decision"] = "excluded"
        result["screening_reason"] = f"below_threshold: {score_reason}"
    return result


def append_screening_columns(fieldnames: list[str]) -> list[str]:
    return fieldnames + [column for column in SCREENING_COLUMNS if column not in fieldnames]


def to_candidate_row(row: dict[str, str], source_raw_file: Path) -> dict[str, str]:
    return {
        "market_type": row["market_type"],
        "market_label": row["market_label"],
        "security_code": row["security_code"],
        "symbol": row.get("symbol", ""),
        "exchange": row.get("exchange", ""),
        "board": row.get("board", ""),
        "listed_company_name": row.get("listed_company_name", ""),
        "security_name": row.get("security_name", ""),
        "currency": row.get("currency", ""),
        "moat_score": row["moat_score"],
        "screening_reason": row["screening_reason"],
        "evidence_sources": row["evidence_sources"],
        "screening_run_at_utc": row["screening_run_at_utc"],
        "source_raw_file": str(source_raw_file),
    }


def run_screening(args: argparse.Namespace) -> tuple[int, int, int]:
    run_at_utc = datetime.now(UTC).replace(microsecond=0).isoformat()
    evidence = load_evidence(args.evidence)
    markets = [
        MarketConfig("A_SHARE", "A股", args.a_share_raw, args.a_share_output),
        MarketConfig("HONG_KONG", "港股", args.hong_kong_raw, args.hong_kong_output),
    ]

    total_rows = 0
    candidate_rows: list[dict[str, str]] = []
    for market in markets:
        fieldnames, rows = read_csv(market.raw_path)
        screened_rows = [
            screen_security(
                security=row,
                market=market,
                evidence=evidence,
                candidate_threshold=args.candidate_threshold,
                run_at_utc=run_at_utc,
            )
            for row in rows
        ]
        write_csv(market.output_path, append_screening_columns(fieldnames), screened_rows)
        candidate_rows.extend(
            to_candidate_row(row, source_raw_file=market.raw_path)
            for row in screened_rows
            if row["screening_decision"] == "candidate"
        )
        total_rows += len(screened_rows)

    candidate_rows = sorted(
        candidate_rows,
        key=lambda row: (row["market_type"], -int(row["moat_score"]), row["security_code"]),
    )
    write_csv(args.candidates_output, CANDIDATE_COLUMNS, candidate_rows)
    return total_rows, len(evidence), len(candidate_rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run evidence-backed moat screening for A-share and Hong Kong securities.")
    parser.add_argument("--a-share-raw", type=Path, default=DEFAULT_A_SHARE_RAW)
    parser.add_argument("--hong-kong-raw", type=Path, default=DEFAULT_HONG_KONG_RAW)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--a-share-output", type=Path, default=DEFAULT_A_SHARE_OUTPUT)
    parser.add_argument("--hong-kong-output", type=Path, default=DEFAULT_HONG_KONG_OUTPUT)
    parser.add_argument("--candidates-output", type=Path, default=DEFAULT_CANDIDATES_OUTPUT)
    parser.add_argument("--candidate-threshold", type=int, default=70)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.candidate_threshold < 0 or args.candidate_threshold > 100:
        raise ScreeningError("--candidate-threshold must be between 0 and 100")

    screened_count, evidence_count, candidate_count = run_screening(args)
    print(f"Screened {screened_count} securities")
    print(f"Loaded {evidence_count} evidence rows")
    print(f"Wrote {candidate_count} watchlist candidates to {args.candidates_output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScreeningError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
