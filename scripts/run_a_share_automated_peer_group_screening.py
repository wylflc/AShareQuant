#!/usr/bin/env python3
"""Screen all remaining A-share companies by peer group.

This is an automated first-pass completion pass. It does not replace manually
calibrated peer-group reviews; it fills the remaining coverage gap with a
conservative capability-first rule so every triaged A-share listed company has
an auditable watch/reject decision.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


DEFAULT_TRIAGE = Path("data/processed/a_share_company_triage_reviews.csv")
DEFAULT_SCORES = Path("data/processed/a_share_full_coverage_scores.csv")
DEFAULT_DECISIONS_DIR = Path("data/processed")
DEFAULT_DECISIONS_OUTPUT = Path("data/processed/a_share_automated_peer_group_decisions.csv")
DEFAULT_SUMMARY_OUTPUT = Path("data/processed/a_share_automated_peer_group_screening_summary.csv")
DECIDED_AT_UTC = "2026-05-15T00:00:00+00:00"
DECISION_SOURCE = "automated_peer_group_screen_v1"

DECISION_COLUMNS = [
    "peer_group",
    "security_code",
    "security_name",
    "prior_preliminary_attention",
    "reviewer_decision",
    "watch_selection_route",
    "decision_source",
    "reviewer_or_inferred_reason",
    "auto_group_rank",
    "triage_score",
    "business_moat_score",
    "technology_barrier_score",
    "market_position_score",
    "business_quality_score",
    "operating_quality_score",
    "industry_outlook_score",
    "governance_risk_score",
    "cyclicality_profile",
    "compounding_profile",
    "analyst_response",
    "calibrated_standard_implication",
    "applies_to_future_markets",
    "source_urls",
    "decided_at_utc",
]

SUMMARY_COLUMNS = [
    "peer_group",
    "screened_company_count",
    "watch_count",
    "reject_for_now_count",
    "low_barrier_group",
    "max_triage_score",
    "average_triage_score",
    "watch_companies",
    "top_rejected_examples",
    "screening_rule",
]

LOW_BARRIER_KEYWORDS = [
    "餐饮",
    "百货",
    "超市",
    "连锁",
    "贸易",
    "专业市场",
    "一般物业经营",
    "装修装饰",
    "建筑装饰设计",
    "旅游服务",
    "房地产开发",
    "房地产服务",
    "园区开发",
    "服装",
    "服饰",
    "家纺",
    "棉纺",
    "毛纺",
    "印染",
    "丝绸",
    "纺织",
    "酒店",
    "住宿",
]


@dataclass(frozen=True)
class AutoDecision:
    row: dict[str, str]
    reviewer_decision: str
    auto_group_rank: int
    reason_type: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--triage", type=Path, default=DEFAULT_TRIAGE)
    parser.add_argument("--scores", type=Path, default=DEFAULT_SCORES)
    parser.add_argument("--decisions-dir", type=Path, default=DEFAULT_DECISIONS_DIR)
    parser.add_argument("--decisions-output", type=Path, default=DEFAULT_DECISIONS_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_existing_decision_codes(decisions_dir: Path, output_path: Path) -> set[str]:
    codes: set[str] = set()
    for path in sorted(decisions_dir.glob("a_share_*_peer_group_decisions.csv")):
        if path.resolve() == output_path.resolve():
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                code = row.get("security_code", "")
                if code:
                    codes.add(code)
    return codes


def f(row: dict[str, str], column: str) -> float:
    try:
        return float(row.get(column, "") or 0.0)
    except ValueError:
        return 0.0


def representative_code(row: dict[str, str]) -> str:
    return row.get("representative_security_code") or row.get("security_code", "")


def is_low_barrier_group(peer_group: str) -> bool:
    return any(keyword in peer_group for keyword in LOW_BARRIER_KEYWORDS)


def is_risk_warning_name(security_name: str) -> bool:
    return "ST" in security_name


def score_tuple(row: dict[str, str]) -> tuple[float, float, float, float, float]:
    return (
        f(row, "triage_score"),
        f(row, "technology_barrier_score"),
        f(row, "business_moat_score"),
        f(row, "market_position_score"),
        f(row, "business_quality_score"),
    )


def passes_watch_threshold(row: dict[str, str]) -> bool:
    peer_group = row.get("peer_group", "")
    security_name = row.get("security_name", "")
    if is_low_barrier_group(peer_group) or is_risk_warning_name(security_name):
        return False

    triage = f(row, "triage_score")
    moat = f(row, "business_moat_score")
    tech = f(row, "technology_barrier_score")
    market = f(row, "market_position_score")
    quality = f(row, "business_quality_score")
    governance = f(row, "governance_risk_score")

    if governance < 58:
        return False
    if triage >= 76 and max(moat, tech, market) >= 78 and quality >= 48:
        return True
    if triage >= 71 and tech >= 86 and moat >= 60 and market >= 52:
        return True
    if triage >= 71 and moat >= 86 and market >= 68 and quality >= 45:
        return True
    if triage >= 73 and market >= 85 and max(moat, tech) >= 66 and quality >= 48:
        return True
    if triage >= 68 and max(moat, tech, market) >= 91 and quality >= 45:
        return True
    return False


def peer_group_cap(group_size: int) -> int:
    if group_size >= 80:
        return 4
    if group_size >= 20:
        return 3
    if group_size >= 8:
        return 2
    return 1


def select_watch_rows(rows: list[dict[str, str]]) -> set[str]:
    by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    all_by_group: Counter[str] = Counter()
    for row in rows:
        peer_group = row.get("peer_group", "")
        all_by_group[peer_group] += 1
        if passes_watch_threshold(row):
            by_group[peer_group].append(row)

    selected: set[str] = set()
    for peer_group, candidates in by_group.items():
        ranked = sorted(candidates, key=score_tuple, reverse=True)
        for row in ranked[: peer_group_cap(all_by_group[peer_group])]:
            selected.add(representative_code(row))
    return selected


def reason_type(row: dict[str, str], selected_codes: set[str]) -> str:
    code = representative_code(row)
    if code in selected_codes:
        return "automated_watch_threshold_pass"
    if is_low_barrier_group(row.get("peer_group", "")):
        return "low_barrier_group_rejection"
    if is_risk_warning_name(row.get("security_name", "")):
        return "risk_warning_rejection"
    if passes_watch_threshold(row):
        return "peer_cap_dominance_rejection"
    if row.get("triage_decision") == "reject":
        return "triage_reject_reaffirmed"
    return "below_automated_watch_threshold"


def inferred_reason(row: dict[str, str], reason: str) -> str:
    if reason == "automated_watch_threshold_pass":
        return "Automated peer-group screen retained this company as one of the strongest remaining companies in its industry group under the capability-first thresholds."
    if reason == "low_barrier_group_rejection":
        return "Automated low-barrier group rejection. The peer group is judged easy to copy with capital and execution, so no company is retained without exceptional source-backed moat evidence."
    if reason == "risk_warning_rejection":
        return "Automated risk-warning rejection. Risk-warning securities require later manual review before watchlist inclusion."
    if reason == "peer_cap_dominance_rejection":
        return "Automated dominance rejection. The company passed initial numerical thresholds but was weaker than higher-ranked peers in the same industry group."
    if reason == "triage_reject_reaffirmed":
        return "Automated rejection reaffirming the first-layer triage result."
    return "Automated rejection because the company did not meet the conservative watch threshold for moat, technology barrier, market position, business quality, and governance."


def analyst_response(row: dict[str, str], decision: str, reason: str) -> str:
    base = (
        f"{row.get('security_name', '')}: triage {f(row, 'triage_score'):.2f}; "
        f"moat {f(row, 'business_moat_score'):.2f}; "
        f"technology {f(row, 'technology_barrier_score'):.2f}; "
        f"market {f(row, 'market_position_score'):.2f}; "
        f"business quality {f(row, 'business_quality_score'):.2f}; "
        f"governance {f(row, 'governance_risk_score'):.2f}."
    )
    if decision == "watch":
        return (
            f"Retained by automated group screening. {base} The company is a first-pass watch candidate and still needs later deep review with authoritative reports."
        )
    if reason == "low_barrier_group_rejection":
        return f"Rejected by whole-group low-barrier rule. {base}"
    if reason == "peer_cap_dominance_rejection":
        return f"Rejected because stronger same-group companies consumed the automated watch slots. {base}"
    return f"Rejected for now by automated group screening. {base}"


def standard_implication(row: dict[str, str], reason: str) -> str:
    if reason == "automated_watch_threshold_pass":
        return "Automated watch is allowed only for top-ranked group companies whose moat, technology barrier, market position, quality, and governance clear conservative thresholds."
    if reason == "low_barrier_group_rejection":
        return "An entire low-barrier industry can contribute zero watchlist companies when durable advantages are weak and competition is easy to attract."
    if reason == "risk_warning_rejection":
        return "Risk-warning names are excluded from automated watchlist inclusion and require explicit manual re-entry evidence."
    if reason == "peer_cap_dominance_rejection":
        return "Passing a numerical threshold is not enough when stronger same-group peers dominate the available attention slots."
    return "Companies below the automated watch threshold remain rejected for now while preserving source-backed triage evidence for future challenge."


def build_rows(
    triage_rows: list[dict[str, str]], scores_by_code: dict[str, dict[str, str]], decided_codes: set[str]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    remaining: list[dict[str, str]] = []
    for row in triage_rows:
        code = representative_code(row)
        if not code or code in decided_codes:
            continue
        merged = dict(scores_by_code.get(code, {}))
        merged.update(row)
        remaining.append(merged)

    selected_codes = select_watch_rows(remaining)
    ranked_by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in remaining:
        ranked_by_group[row.get("peer_group", "")].append(row)
    for group_rows in ranked_by_group.values():
        group_rows.sort(key=score_tuple, reverse=True)

    rank_lookup: dict[str, int] = {}
    for group_rows in ranked_by_group.values():
        for rank, row in enumerate(group_rows, start=1):
            rank_lookup[representative_code(row)] = rank

    decisions: list[dict[str, str]] = []
    for row in sorted(remaining, key=lambda item: (item.get("peer_group", ""), -f(item, "triage_score"), representative_code(item))):
        code = representative_code(row)
        decision = "watch" if code in selected_codes else "reject_for_now"
        reason = reason_type(row, selected_codes)
        decisions.append(
            {
                "peer_group": row.get("peer_group", ""),
                "security_code": code,
                "security_name": row.get("security_name", ""),
                "prior_preliminary_attention": row.get("triage_decision", ""),
                "reviewer_decision": decision,
                "watch_selection_route": "boundary_judged_watch" if decision == "watch" else "",
                "decision_source": DECISION_SOURCE,
                "reviewer_or_inferred_reason": inferred_reason(row, reason),
                "auto_group_rank": str(rank_lookup.get(code, "")),
                "triage_score": f(row, "triage_score"),
                "business_moat_score": f(row, "business_moat_score"),
                "technology_barrier_score": f(row, "technology_barrier_score"),
                "market_position_score": f(row, "market_position_score"),
                "business_quality_score": f(row, "business_quality_score"),
                "operating_quality_score": f(row, "operating_quality_score"),
                "industry_outlook_score": f(row, "industry_outlook_score"),
                "governance_risk_score": f(row, "governance_risk_score"),
                "cyclicality_profile": row.get("cyclicality_profile", ""),
                "compounding_profile": row.get("compounding_profile", ""),
                "analyst_response": analyst_response(row, decision, reason),
                "calibrated_standard_implication": standard_implication(row, reason),
                "applies_to_future_markets": "false",
                "source_urls": row.get("source_score_urls") or row.get("source_urls", ""),
                "decided_at_utc": DECIDED_AT_UTC,
            }
        )

    summaries = summarize(decisions)
    return decisions, summaries


def summarize(decisions: list[dict[str, str]]) -> list[dict[str, str]]:
    by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in decisions:
        by_group[row["peer_group"]].append(row)

    summaries: list[dict[str, str]] = []
    for peer_group, rows in by_group.items():
        scores = [float(row["triage_score"]) for row in rows]
        watch_rows = [row for row in rows if row["reviewer_decision"] == "watch"]
        rejected_rows = [row for row in rows if row["reviewer_decision"] != "watch"]
        top_rejected = sorted(rejected_rows, key=lambda row: float(row["triage_score"]), reverse=True)[:5]
        summaries.append(
            {
                "peer_group": peer_group,
                "screened_company_count": str(len(rows)),
                "watch_count": str(len(watch_rows)),
                "reject_for_now_count": str(len(rejected_rows)),
                "low_barrier_group": str(is_low_barrier_group(peer_group)).lower(),
                "max_triage_score": f"{max(scores):.2f}" if scores else "",
                "average_triage_score": f"{mean(scores):.2f}" if scores else "",
                "watch_companies": " | ".join(f"{row['security_code']}:{row['security_name']}" for row in watch_rows),
                "top_rejected_examples": " | ".join(
                    f"{row['security_code']}:{row['security_name']}:{float(row['triage_score']):.2f}" for row in top_rejected
                ),
                "screening_rule": "low_barrier_zero_watch_allowed"
                if is_low_barrier_group(peer_group)
                else "conservative_capability_first_peer_group_threshold",
            }
        )
    summaries.sort(key=lambda row: (-int(row["screened_company_count"]), row["peer_group"]))
    return summaries


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    scores_by_code = {row["security_code"]: row for row in read_csv(args.scores)}
    decided_codes = read_existing_decision_codes(args.decisions_dir, args.decisions_output)
    decisions, summaries = build_rows(read_csv(args.triage), scores_by_code, decided_codes)
    write_csv(args.decisions_output, decisions, DECISION_COLUMNS)
    write_csv(args.summary_output, summaries, SUMMARY_COLUMNS)
    print(f"wrote {len(decisions)} decisions to {args.decisions_output}")
    print(f"wrote {len(summaries)} peer-group summaries to {args.summary_output}")
    print(f"automated watch decisions: {sum(1 for row in decisions if row['reviewer_decision'] == 'watch')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
