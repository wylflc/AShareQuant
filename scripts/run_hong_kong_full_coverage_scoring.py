#!/usr/bin/env python3
"""Create dimensional Hong Kong moat scores from fetched research evidence."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path


DEFAULT_RAW = Path("data/raw/hong_kong_securities.csv")
DEFAULT_PROFILES = Path("data/interim/hong_kong_company_profiles.csv")
DEFAULT_FINANCIALS = Path("data/interim/hong_kong_financial_indicators.csv")
DEFAULT_OUTPUT = Path("data/processed/hong_kong_full_coverage_scores.csv")
DEFAULT_WATCHLIST = Path("data/processed/hong_kong_full_coverage_watchlist.csv")
SCORING_MODEL_VERSION = "full_coverage_dimensional_v0.1"

DIMENSIONS = [
    ("business_moat", 0.25),
    ("technology_barrier", 0.20),
    ("market_position", 0.15),
    ("business_quality", 0.15),
    ("operating_quality", 0.15),
    ("governance_risk", 0.10),
]
DIMENSION_WEIGHT_POINTS = {
    "business_moat": 25,
    "technology_barrier": 20,
    "market_position": 15,
    "business_quality": 15,
    "operating_quality": 15,
    "governance_risk": 10,
}

OUTPUT_COLUMNS = [
    "market_type",
    "market_label",
    "security_code",
    "symbol",
    "exchange",
    "board",
    "listed_company_name",
    "security_name",
    "currency",
    "isin",
    "listing_date",
    "industry",
    "eligibility_status",
    "screening_status",
    "disclosure_status",
    "peer_group",
    "peer_relative_position",
    "business_moat_score",
    "business_moat_level",
    "business_moat_reason",
    "technology_barrier_score",
    "technology_barrier_level",
    "technology_barrier_reason",
    "market_position_score",
    "market_position_level",
    "market_position_reason",
    "business_quality_score",
    "business_quality_level",
    "business_quality_reason",
    "operating_quality_score",
    "operating_quality_level",
    "operating_quality_reason",
    "governance_risk_score",
    "governance_risk_level",
    "governance_risk_reason",
    "weighted_total_score",
    "overall_level",
    "overall_reason",
    "evidence_confidence",
    "source_urls",
    "reviewed_at_utc",
    "scoring_model_version",
]

WATCHLIST_COLUMNS = [
    "market_type",
    "market_label",
    "security_code",
    "symbol",
    "exchange",
    "board",
    "listed_company_name",
    "security_name",
    "currency",
    "industry",
    "peer_group",
    "peer_relative_position",
    "weighted_total_score",
    "overall_level",
    "overall_reason",
    "source_urls",
    "reviewed_at_utc",
    "scoring_model_version",
]


class ScoringError(RuntimeError):
    """Raised when Hong Kong full-coverage scoring inputs are invalid."""


@dataclass(frozen=True)
class IndustryPrior:
    business_moat: int
    technology_barrier: int
    business_quality: int
    capital_replicability: str


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise ScoringError(f"CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if not reader.fieldnames:
            raise ScoringError(f"CSV has no header: {path}")
        return list(reader.fieldnames), rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def by_code(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    _, rows = read_csv(path)
    return {row["security_code"]: row for row in rows if row.get("security_code")}


def f(value: str | None) -> float | None:
    if value in (None, "", "--"):
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def weighted_score(scores: dict[str, int]) -> int:
    numerator = sum(scores[name] * DIMENSION_WEIGHT_POINTS[name] for name in DIMENSION_WEIGHT_POINTS)
    return max(0, min(100, (numerator + 50) // 100))


def level(score: int) -> str:
    if score >= 90:
        return "S"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "E"


def parse_date(raw: str) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def percentile_maps(rows: list[dict[str, str]], peer_key: str, metric: str, reverse: bool = False) -> dict[str, float]:
    by_peer: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        value = f(row.get(metric))
        if value is None:
            continue
        by_peer.setdefault(row[peer_key], []).append((row["security_code"], value))
    result: dict[str, float] = {}
    for items in by_peer.values():
        values = sorted(value for _, value in items)
        if len(values) == 1:
            for code, _ in items:
                result[code] = 50.0
            continue
        for code, value in items:
            rank = values.index(value)
            pct = 100 * (1 - rank / (len(values) - 1)) if reverse else 100 * rank / (len(values) - 1)
            result[code] = pct
    return result


def keyword_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def industry_prior(peer_group: str, profile_text: str) -> IndustryPrior:
    text = f"{peer_group} {profile_text}"
    lower_text = text.lower()
    industry_text = peer_group
    lower_industry = industry_text.lower()
    if keyword_any(industry_text, ["银行", "保险", "金融", "证券", "信托", "资产管理"]) or keyword_any(lower_industry, ["bank", "insurance", "financial", "securities", "asset management"]):
        return IndustryPrior(72, 45, 64, "licenses regulation customer relationships and risk systems reduce pure capital replicability")
    if keyword_any(industry_text, ["公用", "电力", "燃气", "水务", "电讯", "电信", "港口", "机场", "高速", "铁路"]) or keyword_any(lower_industry, ["utilities", "power", "gas", "water", "telecommunication", "port", "airport", "railway"]):
        return IndustryPrior(78, 42, 72, "regulated infrastructure assets concessions and network coverage are difficult to buy quickly")
    if keyword_any(industry_text, ["软件", "资讯科技", "互联网", "媒体", "游戏", "电子商贸"]) or keyword_any(lower_industry, ["software", "internet", "media", "games", "e-commerce", "services"]):
        return IndustryPrior(66, 72, 62, "platform data user network and product capability require more than capital")
    if keyword_any(industry_text, ["药", "医疗", "生物", "保健"]) or keyword_any(lower_industry, ["pharmaceutical", "biotech", "health care", "healthcare", "medical"]):
        return IndustryPrior(65, 76, 62, "clinical validation regulation distribution and trust limit pure capital entry")
    if keyword_any(industry_text, ["半导体", "芯片", "电子", "硬件"]) or keyword_any(lower_industry, ["semiconductor", "chip", "electronics", "hardware"]):
        return IndustryPrior(62, 78, 58, "process know how supply chain qualification and customer validation take time")
    if keyword_any(industry_text, ["汽车", "电池", "新能源", "光伏", "能源设备"]) or keyword_any(lower_industry, ["automobile", "battery", "new energy", "solar", "energy equipment"]):
        return IndustryPrior(58, 70, 54, "manufacturing scale helps but process yield supply chain and customers are not instantly bought")
    if keyword_any(industry_text, ["食品", "饮料", "酒", "服饰", "体育用品", "化妆", "消费品"]) or keyword_any(lower_industry, ["food", "beverage", "apparel", "sportswear", "cosmetic", "consumer"]):
        return IndustryPrior(74, 45, 70, "consumer brand channel and product trust are costly to replicate quickly")
    if keyword_any(industry_text, ["地产", "物业", "建筑", "建材"]) or keyword_any(lower_industry, ["properties", "property", "construction", "building materials"]):
        return IndustryPrior(42, 38, 38, "land project access leverage and execution are cyclical and comparatively replicable")
    if keyword_any(industry_text, ["零售", "百货", "超市", "贸易", "批发"]) or keyword_any(lower_industry, ["retail", "department store", "supermarket", "trading", "wholesale"]):
        return IndustryPrior(42, 35, 45, "store formats logistics and distribution can often be replicated with capital")
    if keyword_any(industry_text, ["博彩", "旅游", "酒店", "餐饮", "教育"]) or keyword_any(lower_industry, ["gaming", "tourism", "hotel", "restaurant", "leisure", "education"]):
        return IndustryPrior(58, 42, 52, "brand location licenses and operations matter but demand can be cyclical")
    if keyword_any(industry_text, ["矿", "石油", "煤", "钢", "金属", "材料", "化工"]) or keyword_any(lower_industry, ["mining", "oil", "coal", "steel", "metal", "materials", "chemical"]):
        return IndustryPrior(52, 58, 50, "resource cost process scale and cycles matter but commodity exposure lowers durability")
    if keyword_any(text, ["研发", "专利", "平台", "算法", "科技", "创新"]) or keyword_any(lower_text, ["research", "r&d", "patent", "platform", "algorithm", "technology", "innovation"]):
        return IndustryPrior(52, 62, 52, "profile suggests technical or product capability but industry classification is broad")
    return IndustryPrior(50, 50, 50, "industry evidence does not show a clearly hard-to-replicate structure")


def pct(percentiles: dict[str, float], code: str, default: float = 50.0) -> float:
    return percentiles.get(code, default)


def peer_position(score: int) -> str:
    if score >= 80:
        return "stronger_than_peers"
    if score >= 65:
        return "above_average"
    if score >= 45:
        return "average"
    if score >= 30:
        return "below_average"
    return "weak"


def source_join(*parts: str) -> str:
    urls: list[str] = []
    for part in parts:
        urls.extend(url for url in part.split(";") if url)
    return ";".join(dict.fromkeys(urls))


def score_row(
    raw: dict[str, str],
    profile: dict[str, str],
    financial: dict[str, str],
    percentiles: dict[str, dict[str, float]],
    reviewed_at: str,
) -> dict[str, str]:
    code = raw["security_code"]
    profile_status = profile.get("fetch_status")
    financial_status = financial.get("fetch_status")
    source_urls = source_join(profile.get("source_url", ""), financial.get("source_url", ""))
    industry = profile.get("industry") or raw.get("sub_category") or raw.get("category") or "unknown"
    peer_group = industry
    listing_date = profile.get("listing_date", "")
    profile_text = profile.get("company_profile", "")
    base = {
        "market_type": "HONG_KONG",
        "market_label": "港股",
        "security_code": code,
        "symbol": raw["symbol"],
        "exchange": raw["exchange"],
        "board": raw["board"],
        "listed_company_name": raw["listed_company_name"],
        "security_name": raw["security_name"],
        "currency": raw.get("currency", ""),
        "isin": raw.get("isin", ""),
        "listing_date": listing_date,
        "industry": industry,
        "eligibility_status": "eligible",
        "peer_group": peer_group,
        "source_urls": source_urls,
        "reviewed_at_utc": reviewed_at,
        "scoring_model_version": SCORING_MODEL_VERSION,
    }
    if profile_status != "fetched":
        listed_at = parse_date(listing_date)
        newly_listed = bool(listed_at and (datetime.now(UTC).date() - listed_at).days < 365)
        status = "insufficient_disclosure" if newly_listed else "pending_research"
        base.update(
            {
                "screening_status": status,
                "disclosure_status": status,
                "peer_relative_position": "hard_to_distinguish",
                "overall_reason": "Awaiting fetched profile evidence; this is a workflow state unless the strict insufficient_disclosure definition applies.",
                "evidence_confidence": "low",
            }
        )
        for name, _ in DIMENSIONS:
            base[f"{name}_score"] = ""
            base[f"{name}_level"] = ""
            base[f"{name}_reason"] = ""
        base["weighted_total_score"] = ""
        base["overall_level"] = ""
        return base

    prior = industry_prior(peer_group, profile_text)
    revenue_pct = pct(percentiles["total_operating_revenue"], code)
    profit_pct = pct(percentiles["parent_net_profit"], code)
    net_pct = pct(percentiles["net_margin_pct"], code)
    roe_pct = pct(percentiles["roe_weighted_pct"], code)
    debt_safety_pct = pct(percentiles["debt_asset_ratio_pct_inverse"], code)
    growth_pct = pct(percentiles["revenue_yoy_pct"], code)
    profit_growth_pct = pct(percentiles["profit_yoy_pct"], code)
    eps_pct = pct(percentiles["eps"], code)
    cash_pct = pct(percentiles["operating_cashflow_per_share"], code)

    keyword_bonus_moat = 0
    profile_text_lower = profile_text.lower()
    if keyword_any(profile_text, ["领先", "龙头", "最大", "独家", "特许", "牌照", "专营", "品牌", "全球"]) or keyword_any(profile_text_lower, ["leading", "largest", "exclusive", "license", "brand", "global"]):
        keyword_bonus_moat += 7
    if keyword_any(profile_text, ["用户", "会员", "客户", "网络", "平台"]) or keyword_any(profile_text_lower, ["user", "member", "customer", "network", "platform"]):
        keyword_bonus_moat += 4
    keyword_bonus_tech = 0
    if keyword_any(profile_text, ["研发", "专利", "算法", "云", "人工智能", "平台", "科技", "技术"]) or keyword_any(profile_text_lower, ["research", "r&d", "patent", "algorithm", "cloud", "artificial intelligence", " ai", "platform", "technology", "technical"]):
        keyword_bonus_tech += 8

    business_moat = clamp(prior.business_moat + (revenue_pct - 50) * 0.18 + (profit_pct - 50) * 0.12 + keyword_bonus_moat)
    technology_barrier = clamp(prior.technology_barrier + keyword_bonus_tech + (eps_pct - 50) * 0.08)
    market_position = clamp(45 + revenue_pct * 0.35 + profit_pct * 0.30 + (prior.business_moat - 50) * 0.20)
    business_quality = clamp(prior.business_quality + (net_pct - 50) * 0.28 + (growth_pct - 50) * 0.10 + (profit_growth_pct - 50) * 0.08)
    operating_quality = clamp(50 + (roe_pct - 50) * 0.30 + (cash_pct - 50) * 0.15 + (debt_safety_pct - 50) * 0.18)
    governance_risk = clamp(68 + (debt_safety_pct - 50) * 0.12)
    weighted = weighted_score(
        {
            "business_moat": business_moat,
            "technology_barrier": technology_barrier,
            "market_position": market_position,
            "business_quality": business_quality,
            "operating_quality": operating_quality,
            "governance_risk": governance_risk,
        }
    )

    confidence = "high" if financial_status == "fetched" and financial.get("total_operating_revenue") else "medium"
    base.update(
        {
            "screening_status": "scored",
            "disclosure_status": "sufficient_public_evidence",
            "peer_relative_position": peer_position(weighted),
            "business_moat_score": str(business_moat),
            "business_moat_level": level(business_moat),
            "business_moat_reason": f"Peer group {peer_group}; capital replicability view: {prior.capital_replicability}; revenue and profit peer percentiles are {revenue_pct:.0f}/{profit_pct:.0f}; profile keywords add {keyword_bonus_moat} points.",
            "technology_barrier_score": str(technology_barrier),
            "technology_barrier_level": level(technology_barrier),
            "technology_barrier_reason": f"Technology prior comes from peer group and profile technology keywords; profile keywords add {keyword_bonus_tech} points and EPS percentile is {eps_pct:.0f}.",
            "market_position_score": str(market_position),
            "market_position_level": level(market_position),
            "market_position_reason": f"Market position uses reported revenue {financial.get('total_operating_revenue', '')} and net profit {financial.get('parent_net_profit', '')} relative to peer group percentiles {revenue_pct:.0f}/{profit_pct:.0f}.",
            "business_quality_score": str(business_quality),
            "business_quality_level": level(business_quality),
            "business_quality_reason": f"Business quality uses net margin {financial.get('net_margin_pct', '')}% revenue growth {financial.get('revenue_yoy_pct', '')}% and profit growth {financial.get('profit_yoy_pct', '')}% against peers.",
            "operating_quality_score": str(operating_quality),
            "operating_quality_level": level(operating_quality),
            "operating_quality_reason": f"Operating quality uses ROE {financial.get('roe_weighted_pct', '')}% operating cash flow per share {financial.get('operating_cashflow_per_share', '')} and debt ratio {financial.get('debt_asset_ratio_pct', '')}%.",
            "governance_risk_score": str(governance_risk),
            "governance_risk_level": level(governance_risk),
            "governance_risk_reason": f"Governance and risk score starts from public disclosure availability and adjusts for balance-sheet pressure; fiscal year end is {profile.get('fiscal_year_end', '')}.",
            "weighted_total_score": str(weighted),
            "overall_level": level(weighted),
            "overall_reason": "Weighted score from six stored dimensions. This first-pass algorithmic score is evidence-backed by Eastmoney HKF10 profile and financial indicators.",
            "evidence_confidence": confidence,
        }
    )
    return base


def run(args: argparse.Namespace) -> tuple[int, int, int]:
    _, raw_rows = read_csv(args.raw)
    profiles = by_code(args.profiles)
    financials = by_code(args.financials)
    reviewed_at = utc_now()
    financial_rows = [
        financials[row["security_code"]] | {"peer_group": profiles.get(row["security_code"], {}).get("industry") or row.get("sub_category") or "unknown"}
        for row in raw_rows
        if financials.get(row["security_code"], {}).get("fetch_status") == "fetched"
    ]
    percentiles = {
        "total_operating_revenue": percentile_maps(financial_rows, "peer_group", "total_operating_revenue"),
        "parent_net_profit": percentile_maps(financial_rows, "peer_group", "parent_net_profit"),
        "net_margin_pct": percentile_maps(financial_rows, "peer_group", "net_margin_pct"),
        "roe_weighted_pct": percentile_maps(financial_rows, "peer_group", "roe_weighted_pct"),
        "debt_asset_ratio_pct_inverse": percentile_maps(financial_rows, "peer_group", "debt_asset_ratio_pct", reverse=True),
        "revenue_yoy_pct": percentile_maps(financial_rows, "peer_group", "revenue_yoy_pct"),
        "profit_yoy_pct": percentile_maps(financial_rows, "peer_group", "profit_yoy_pct"),
        "eps": percentile_maps(financial_rows, "peer_group", "eps"),
        "operating_cashflow_per_share": percentile_maps(financial_rows, "peer_group", "operating_cashflow_per_share"),
    }
    output_rows = [
        score_row(raw=row, profile=profiles.get(row["security_code"], {}), financial=financials.get(row["security_code"], {}), percentiles=percentiles, reviewed_at=reviewed_at)
        for row in raw_rows
    ]
    pending_count = sum(1 for row in output_rows if row["screening_status"] == "pending_research")
    if args.require_complete and pending_count:
        raise ScoringError(f"{pending_count} Hong Kong rows are still pending research evidence")
    write_csv(args.output, OUTPUT_COLUMNS, output_rows)
    watchlist_rows = [
        {column: row[column] for column in WATCHLIST_COLUMNS}
        for row in output_rows
        if row["screening_status"] == "scored" and row["weighted_total_score"] and int(row["weighted_total_score"]) >= args.candidate_threshold
    ]
    watchlist_rows.sort(key=lambda row: (-int(row["weighted_total_score"]), row["security_code"]))
    write_csv(args.watchlist, WATCHLIST_COLUMNS, watchlist_rows)
    return len(output_rows), sum(1 for row in output_rows if row["screening_status"] == "scored"), len(watchlist_rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Hong Kong full-coverage dimensional moat scoring.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--financials", type=Path, default=DEFAULT_FINANCIALS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--watchlist", type=Path, default=DEFAULT_WATCHLIST)
    parser.add_argument("--candidate-threshold", type=int, default=70)
    parser.add_argument("--require-complete", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    total_count, scored_count, watchlist_count = run(args)
    print(f"Wrote {total_count} Hong Kong screening rows to {args.output}")
    print(f"Scored {scored_count} rows with fetched evidence")
    print(f"Wrote {watchlist_count} watchlist rows to {args.watchlist}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScoringError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
