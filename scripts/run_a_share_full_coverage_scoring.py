#!/usr/bin/env python3
"""Create dimensional A-share moat scores from fetched research evidence."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path


DEFAULT_RAW = Path("data/raw/a_share_securities.csv")
DEFAULT_QUEUE = Path("data/interim/a_share_research_queue.csv")
DEFAULT_PROFILES = Path("data/interim/a_share_company_profiles.csv")
DEFAULT_FINANCIALS = Path("data/interim/a_share_financial_indicators.csv")
DEFAULT_OUTPUT = Path("data/processed/a_share_full_coverage_scores.csv")
DEFAULT_WATCHLIST = Path("data/processed/a_share_full_coverage_watchlist.csv")
SCORING_MODEL_VERSION = "full_coverage_dimensional_v0.4"

DIMENSIONS = [
    ("business_moat", 0.28),
    ("technology_barrier", 0.24),
    ("market_position", 0.14),
    ("business_quality", 0.08),
    ("operating_quality", 0.06),
    ("industry_outlook", 0.14),
    ("governance_risk", 0.06),
]
DIMENSION_WEIGHT_POINTS = {
    "business_moat": 28,
    "technology_barrier": 24,
    "market_position": 14,
    "business_quality": 8,
    "operating_quality": 6,
    "industry_outlook": 14,
    "governance_risk": 6,
}

OUTPUT_COLUMNS = [
    "security_code",
    "symbol",
    "exchange",
    "board",
    "listed_company_name",
    "security_name",
    "listing_date",
    "industry",
    "eligibility_status",
    "screening_status",
    "disclosure_status",
    "peer_group",
    "peer_relative_position",
    "cyclicality_profile",
    "compounding_profile",
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
    "industry_outlook_score",
    "industry_outlook_level",
    "industry_outlook_reason",
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
    "security_code",
    "security_name",
    "score_total",
    "score_business_moat",
    "score_technology_barrier",
    "score_market_position",
    "score_business_quality",
    "score_operating_quality",
    "score_industry_outlook",
    "score_governance_risk",
    "peer_group",
    "peer_relative_position",
    "scoring_model_version",
]

WATCHLIST_SCORE_FIELDS = [
    ("score_total", "总分", "weighted_total_score"),
    ("score_business_moat", "护城河", "business_moat_score"),
    ("score_technology_barrier", "技术壁垒", "technology_barrier_score"),
    ("score_market_position", "市场地位", "market_position_score"),
    ("score_business_quality", "商业质量", "business_quality_score"),
    ("score_operating_quality", "经营质量", "operating_quality_score"),
    ("score_industry_outlook", "行业前景", "industry_outlook_score"),
    ("score_governance_risk", "治理风险", "governance_risk_score"),
]


class ScoringError(RuntimeError):
    """Raised when full-coverage scoring inputs are invalid."""


@dataclass(frozen=True)
class IndustryPrior:
    business_moat: int
    technology_barrier: int
    business_quality: int
    capital_replicability: str


@dataclass(frozen=True)
class IndustryOutlook:
    score: float
    cyclicality_profile: str
    compounding_profile: str
    reason: str


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
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def clamp(value: float, low: int = 0, high: int = 100) -> float:
    return round(max(low, min(high, float(value))), 2)


def weighted_score(scores: dict[str, float]) -> float:
    numerator = sum(scores[name] * DIMENSION_WEIGHT_POINTS[name] for name in DIMENSION_WEIGHT_POINTS)
    return clamp(numerator / 100)


def fmt_score(score: float) -> str:
    return f"{score:.2f}"


def level(score: float) -> str:
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
    text = raw[:10]
    try:
        return date.fromisoformat(text)
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
            if reverse:
                pct = 100 * (1 - rank / (len(values) - 1))
            else:
                pct = 100 * rank / (len(values) - 1)
            result[code] = pct
    return result


def peer_size_map(rows: list[dict[str, str]], peer_key: str) -> dict[str, float]:
    by_peer: dict[str, list[str]] = {}
    for row in rows:
        by_peer.setdefault(row[peer_key], []).append(row["security_code"])
    return {code: float(len(codes)) for codes in by_peer.values() for code in codes}


def keyword_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def resource_leader_signal(industry_text: str, profile_text: str) -> bool:
    if not keyword_any(industry_text, ["矿", "黄金", "铜", "有色", "金属", "煤炭", "石油"]):
        return False
    signals = [
        keyword_any(profile_text, ["全球", "跨国矿业", "全球领先", "世界", "重要矿业基地"]),
        keyword_any(profile_text, ["自主勘查", "逆周期并购", "资源获取成本", "资源优先", "资源量", "储量", "重要成矿带"]),
        keyword_any(profile_text, ["矿石流五环归一", "低品位", "难处理", "矿业工程", "采矿", "选矿", "冶炼"]),
        keyword_any(profile_text, ["全球前", "位居前", "全球排名", "龙头", "前3位", "前4位"]),
    ]
    return sum(signals) >= 3


def strategic_critical_material_signal(industry_text: str, profile_text: str) -> bool:
    text = f"{industry_text} {profile_text}"
    if not keyword_any(text, ["锗", "镓", "铟", "钨", "钼", "锑", "钽", "铍", "稀散", "稀有小金属", "化合物半导体", "砷化镓", "磷化铟"]):
        return False
    signals = [
        keyword_any(text, ["矿", "资源", "储量", "采矿权", "探矿权", "自有矿山", "完整产业链"]),
        keyword_any(text, ["精深加工", "高纯", "晶片", "单晶", "红外", "光纤", "空间", "半导体材料"]),
        keyword_any(text, ["国家级企业技术中心", "工程技术研究中心", "行业标准", "国家标准", "单项冠军", "专精特新"]),
        keyword_any(text, ["出口管制", "战略资源", "关键材料", "卡脖子", "国产替代"]),
    ]
    return sum(signals) >= 2


def grid_core_equipment_signal(industry_text: str, profile_text: str) -> bool:
    text = f"{industry_text} {profile_text}"
    if not keyword_any(text, ["输变电", "变压器", "电抗器", "互感器", "特高压", "超高压", "换流阀", "直流输电", "电网"]):
        return False
    signals = [
        keyword_any(text, ["特高压", "超高压", "交直流", "高压直流", "换流阀", "首台套"]),
        keyword_any(text, ["国家电网", "南方电网", "国家重大项目", "示范工程", "一体化集成", "境外机电行业输变电", "电力工程施工总承包特级资质"]),
        keyword_any(text, ["全球领先", "全球市场份额领先", "全球高端输变电", "世界领先", "国际领先", "行业领先", "行业前列", "产能稳居", "中国电气工业100强第1位", "大型能源装备"]),
        keyword_any(text, ["国家级", "企业技术中心", "高新技术企业", "专精特新", "进口替代", "创新100强"]),
    ]
    return sum(signals) >= 2


def baijiu_long_cycle_signal(industry_text: str, profile_text: str) -> bool:
    text = f"{industry_text} {profile_text}"
    return keyword_any(industry_text, ["白酒"]) and keyword_any(text, ["酱香", "浓香", "窖池", "窖藏", "陈酿", "基酒", "发酵", "传统工艺", "稀缺产区"])


def cross_market_leader_signal(industry_text: str, profile_text: str) -> bool:
    if keyword_any(industry_text, ["电力", "水务", "燃气", "高速", "港口", "机场", "铁路", "公用"]):
        return True
    if strategic_critical_material_signal(industry_text, profile_text) or grid_core_equipment_signal(industry_text, profile_text):
        return True
    if keyword_any(profile_text, ["国家地理标志", "品牌价值", "驰名商标", "酱香", "稀缺产区", "特许", "牌照", "专营", "垄断"]):
        return True
    if keyword_any(profile_text, ["全球领先", "全球前", "世界领先", "全球最大", "国际领先", "跨国矿业"]):
        return True
    return resource_leader_signal(industry_text, profile_text)


def industry_prior(peer_group: str, raw_industry: str, profile_text: str) -> IndustryPrior:
    industry_text = f"{peer_group} {raw_industry}"
    fallback_text = f"{industry_text} {profile_text}"
    if strategic_critical_material_signal(industry_text, profile_text):
        return IndustryPrior(74, 82, 58, "strategic scarce materials combine resource access, purification, crystal or compound processing, standards, and customer qualification that capital alone cannot compress quickly")
    if grid_core_equipment_signal(industry_text, profile_text):
        return IndustryPrior(72, 78, 62, "ultra-high-voltage grid equipment requires long engineering accumulation, safety validation, grid qualification, and project references that capital alone cannot buy quickly")
    if keyword_any(industry_text, ["白酒"]) or baijiu_long_cycle_signal(industry_text, profile_text):
        return IndustryPrior(84, 68, 82, "top baijiu brands combine origin scarcity, long-cycle brewing, base-liquor inventory, quality consistency, channel trust, and pricing power")
    if keyword_any(industry_text, ["饮料", "食品", "乳", "调味"]):
        return IndustryPrior(72, 48, 68, "consumer brand channel and product trust can matter, but ordinary food process know-how is more replicable than scarce-origin long-cycle categories")
    if keyword_any(industry_text, ["银行", "保险", "证券", "金融"]):
        return IndustryPrior(72, 45, 64, "licenses regulation customer deposits and risk systems reduce pure capital replicability")
    if keyword_any(industry_text, ["电力", "水务", "燃气", "高速", "港口", "机场", "铁路", "公用"]):
        return IndustryPrior(78, 42, 72, "regulated infrastructure assets and concessions are difficult to buy into quickly")
    if keyword_any(industry_text, ["半导体", "芯片", "集成电路", "光刻", "电子设备"]):
        return IndustryPrior(62, 78, 58, "capital is necessary but process know how customers and supply chain qualification take time")
    if keyword_any(industry_text, ["医药", "医疗器械", "生物", "创新药", "疫苗"]):
        return IndustryPrior(65, 76, 62, "clinical validation regulatory approvals and hospital trust limit pure capital entry")
    if keyword_any(industry_text, ["软件", "云", "互联网", "人工智能", "信息技术", "网络安全"]):
        return IndustryPrior(64, 72, 62, "software and data advantages can scale but require product execution and customer adoption")
    if keyword_any(industry_text, ["电池", "储能", "锂电", "电源设备"]):
        return IndustryPrior(68, 82, 58, "battery leaders require chemistry process yield safety validation supply chain and customer qualification that capital alone cannot compress quickly")
    if keyword_any(industry_text, ["新能源", "光伏", "汽车", "电气机械"]):
        return IndustryPrior(58, 70, 54, "manufacturing scale helps but process yield supply chain and customers are not instantly bought")
    if keyword_any(industry_text, ["机械", "设备", "自动化", "仪器仪表", "专用设备"]):
        return IndustryPrior(55, 66, 55, "engineering experience and customer qualification matter but some capacity is replicable")
    if resource_leader_signal(industry_text, profile_text):
        return IndustryPrior(66, 68, 56, "scarce resource base global mine portfolio exploration M&A integration and mining-engineering know-how reduce pure capital replicability despite commodity exposure")
    if keyword_any(industry_text, ["化工", "材料", "有色", "钢铁", "煤炭", "石油"]):
        return IndustryPrior(52, 58, 50, "resource cost process scale and cycles matter but commodity exposure lowers durability")
    if keyword_any(industry_text, ["房地产", "建筑", "装饰", "园林"]):
        return IndustryPrior(42, 38, 38, "land capital project access and leverage are comparatively replicable and cyclical")
    if keyword_any(industry_text, ["零售", "商贸", "批发", "超市", "百货"]):
        return IndustryPrior(42, 35, 45, "store formats and distribution can often be replicated with capital and execution")
    if keyword_any(fallback_text, ["研发", "专利", "核心技术", "平台", "算法"]):
        return IndustryPrior(52, 62, 52, "profile suggests technical or product capability but industry classification is not specific enough")
    return IndustryPrior(50, 50, 50, "industry evidence does not show a clearly hard-to-replicate structure")


def industry_outlook(peer_group: str, raw_industry: str, profile_text: str) -> IndustryOutlook:
    industry_text = f"{peer_group} {raw_industry}"
    fallback_text = f"{industry_text} {profile_text}"
    if strategic_critical_material_signal(industry_text, profile_text):
        return IndustryOutlook(72, "strategic_critical_material_cycle", "resource_technology_optionality", "Strategic scarce materials can benefit from semiconductors, aerospace, AI infrastructure, optical communication, and supply-security demand; price cycles and capacity ramp risks still keep the score below elite compounders.")
    if grid_core_equipment_signal(industry_text, profile_text):
        return IndustryOutlook(68, "grid_capex_structural_growth", "installed_base_and_engineering_compounding", "Grid modernization, UHV transmission, renewable power integration, and overseas power-infrastructure demand support long-cycle growth, though customer capex cycles and project timing remain material.")
    if keyword_any(industry_text, ["软件", "计算机", "云", "互联网", "人工智能", "网络安全", "算力"]):
        return IndustryOutlook(78, "low_to_moderate_cyclicality", "compound_growth", "Digitalization, data, AI, and software adoption support multi-year demand; execution and customer retention still separate leaders from followers.")
    if keyword_any(industry_text, ["电池", "储能", "锂电", "电源设备"]) or keyword_any(profile_text, ["动力电池", "锂电池", "储能系统"]):
        return IndustryOutlook(76, "structural_growth_with_manufacturing_cycle", "scale_and_process_compounding", "EV and storage demand have a long runway, but manufacturing capacity, material prices, and customer inventory cycles can still pressure returns.")
    if keyword_any(industry_text, ["半导体", "芯片", "集成电路", "光刻", "电子设备", "电子元件", "通信设备", "机器人", "自动化", "高端装备", "仪器仪表"]):
        return IndustryOutlook(72, "cyclical_structural_growth", "innovation_compounding", "AI, localization, electrification, and automation support demand, while semiconductor and capex cycles make earnings less linear.")
    if keyword_any(industry_text, ["医药", "医疗器械", "生物医药", "创新药", "疫苗", "诊断"]):
        return IndustryOutlook(70, "defensive_growth_with_policy_risk", "innovation_or_brand_compounding", "Aging, clinical demand, and medical innovation support long-term growth, but pricing, procurement, and trial risks require discounting.")
    if keyword_any(industry_text, ["白酒"]):
        return IndustryOutlook(76, "low_cyclicality", "brand_and_origin_compounding", "Top baijiu demand is mature but durable; scarce origin, long production cycles, brand trust, channel depth, and pricing power can support compounding without relying on high industry volume growth.")
    if keyword_any(industry_text, ["饮料", "食品", "乳", "调味", "消费品"]):
        return IndustryOutlook(70, "low_to_moderate_cyclicality", "brand_compounding", "Staple consumption and trusted brands can compound through pricing, channel depth, and habit, but ordinary packaged foods usually have lower scarcity than top baijiu.")
    if keyword_any(industry_text, ["电力", "水务", "燃气", "高速", "港口", "机场", "铁路", "公用"]):
        return IndustryOutlook(62, "low_cyclicality", "regulated_stable_compounding", "Regulated infrastructure can produce stable demand and cash flow, but returns are usually capped by regulation and asset intensity.")
    if keyword_any(industry_text, ["银行", "保险", "证券", "金融"]):
        return IndustryOutlook(54, "macro_credit_cycle", "balance_sheet_compounding", "Financial companies can compound through risk control and deposits or distribution, but credit, rates, and capital cycles constrain durability.")
    if keyword_any(industry_text, ["新能源", "光伏", "汽车", "电气机械"]):
        return IndustryOutlook(60, "high_competition_growth_cycle", "scale_compounding_if_leader", "Electrification is a structural growth area, but oversupply, price competition, and technology shifts make many manufacturers cyclical.")
    if keyword_any(industry_text, ["机械", "设备", "仪器仪表", "专用设备"]):
        return IndustryOutlook(58, "capex_cycle", "selective_compounding", "Equipment demand follows customer capex cycles; leaders with installed bases and process know-how can compound better than generic capacity suppliers.")
    if resource_leader_signal(industry_text, profile_text):
        return IndustryOutlook(64, "strategic_resource_cycle", "resource_and_process_compounding", "Commodity prices still create cycles, but scarce reserves, reserve replacement, low-cost development, and global mine integration can support leader-level compounding.")
    if keyword_any(industry_text, ["房地产", "建筑", "装饰", "园林", "建材"]):
        return IndustryOutlook(36, "deep_cyclical_or_structural_headwind", "limited_compounding", "Property-linked demand faces leverage, demographic, and investment-cycle pressure, so capital-heavy growth deserves a lower structural outlook.")
    if keyword_any(industry_text, ["零售", "商贸", "批发", "超市", "百货"]):
        return IndustryOutlook(44, "consumer_cycle_competitive", "weak_or_selective_compounding", "Generic retail and distribution are usually easy to replicate with capital, leases, and execution unless a company has clear scale or brand data advantages.")
    if keyword_any(industry_text, ["化工", "材料", "有色", "钢铁", "煤炭", "石油", "矿"]):
        return IndustryOutlook(42, "commodity_cycle", "low_compounding", "Commodity and upstream material earnings are often driven by price and capex cycles rather than internally controlled compounding.")
    if keyword_any(industry_text, ["旅游", "酒店", "餐饮", "博彩", "教育", "影视"]):
        return IndustryOutlook(48, "demand_or_policy_cycle", "brand_location_compounding_if_leader", "Demand can recover and brands or locations matter, but policy exposure, discretionary spending, and operating leverage reduce compounding quality.")
    if keyword_any(fallback_text, ["研发", "专利", "核心技术", "算法", "平台技术", "工业软件"]):
        return IndustryOutlook(56, "unclear_cycle_with_possible_innovation_tailwind", "selective_compounding", "Profile language suggests product or technology optionality, but the industry evidence is too broad for a high structural-outlook score.")
    return IndustryOutlook(50, "unclear_cycle", "unproven_compounding", "Industry evidence does not support a clear structural tailwind or durable compounding profile beyond company-specific execution.")


def pct(percentiles: dict[str, float], code: str, default: float = 50.0) -> float:
    return percentiles.get(code, default)


def peer_position(score: float) -> str:
    if score >= 80:
        return "stronger_than_peers"
    if score >= 65:
        return "above_average"
    if score >= 45:
        return "average"
    if score >= 30:
        return "below_average"
    return "weak"


def watchlist_row(row: dict[str, str]) -> dict[str, str]:
    result = {
        "security_code": row["security_code"],
        "security_name": row["security_name"],
        "peer_group": row["peer_group"],
        "peer_relative_position": row["peer_relative_position"],
        "scoring_model_version": row["scoring_model_version"],
    }
    for output_column, label, source_column in WATCHLIST_SCORE_FIELDS:
        result[output_column] = f"{label}-{row[source_column]}"
    return result


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
    source_urls = ";".join(
        part
        for part in [profile.get("source_url", ""), financial.get("source_urls", "")]
        if part
    )
    peer_group = profile.get("eastmoney_industry") or profile.get("csrc_industry") or raw.get("industry") or "unknown"

    base = {
        "security_code": code,
        "symbol": raw["symbol"],
        "exchange": raw["exchange"],
        "board": raw["board"],
        "listed_company_name": raw["listed_company_name"],
        "security_name": raw["security_name"],
        "listing_date": raw["listing_date"],
        "industry": raw["industry"],
        "eligibility_status": "eligible",
        "peer_group": peer_group,
        "source_urls": source_urls,
        "reviewed_at_utc": reviewed_at,
        "scoring_model_version": SCORING_MODEL_VERSION,
    }

    if profile_status != "fetched" or financial_status != "fetched":
        base.update(
            {
                "screening_status": "pending_research",
                "disclosure_status": "pending_research",
                "peer_relative_position": "hard_to_distinguish",
                "overall_reason": "Awaiting fetched profile and financial evidence; this is a workflow state unless the strict insufficient_disclosure definition applies.",
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

    annual_date = parse_date(financial.get("latest_annual_report_date", ""))
    if raw.get("security_name") == "-" or (annual_date is not None and annual_date.year < 2023):
        base.update(
            {
                "eligibility_status": "inactive_or_not_currently_traded",
                "screening_status": "not_eligible_inactive_security",
                "disclosure_status": "historical_listing_or_no_current_reports",
                "peer_relative_position": "hard_to_distinguish",
                "overall_reason": "Excluded from current listed-company watchlist workflow because the raw row appears historical or inactive; raw universe remains unchanged for audit.",
                "evidence_confidence": "medium",
            }
        )
        for name, _ in DIMENSIONS:
            base[f"{name}_score"] = ""
            base[f"{name}_level"] = ""
            base[f"{name}_reason"] = ""
        base["weighted_total_score"] = ""
        base["overall_level"] = ""
        return base

    profile_text = f"{profile.get('org_profile', '')} {profile.get('business_scope', '')}"
    industry_text = f"{peer_group} {raw.get('industry', '')}"
    prior = industry_prior(peer_group, raw.get("industry", ""), profile_text)
    outlook = industry_outlook(peer_group, raw.get("industry", ""), profile_text)
    revenue_pct = pct(percentiles["total_operating_revenue"], code)
    profit_pct = pct(percentiles["parent_net_profit"], code)
    gross_pct = pct(percentiles["gross_margin_pct"], code)
    net_pct = pct(percentiles["net_margin_pct"], code)
    roe_pct = pct(percentiles["roe_weighted_pct"], code)
    roic_pct = pct(percentiles["roic_pct"], code)
    cash_pct = pct(percentiles["cashflow_to_revenue_pct"], code)
    debt_safety_pct = pct(percentiles["debt_asset_ratio_pct_inverse"], code)
    rd_pct = pct(percentiles["research_expense_to_revenue_pct"], code)
    growth_pct = pct(percentiles["revenue_yoy_pct"], code)

    keyword_bonus_moat = 0
    if keyword_any(profile_text, ["国家地理标志", "品牌价值", "驰名商标", "知名品牌"]):
        keyword_bonus_moat += 3
    if keyword_any(profile_text, ["独家", "特许", "垄断", "牌照", "专营"]):
        keyword_bonus_moat += 3
    if keyword_any(profile_text, ["全球领先", "全球前", "世界领先", "行业龙头", "龙头", "最大", "唯一", "首家"]):
        keyword_bonus_moat += 3
    keyword_bonus_moat = min(keyword_bonus_moat, 6)

    product_process_bonus_tech = 0
    capability_moat_bonus = 0
    capability_market_bonus = 0
    strategic_material = strategic_critical_material_signal(industry_text, profile_text)
    grid_core_equipment = grid_core_equipment_signal(industry_text, profile_text)
    baijiu_long_cycle = baijiu_long_cycle_signal(industry_text, profile_text)
    if baijiu_long_cycle:
        product_process_bonus_tech += 18
        capability_moat_bonus += 6
        capability_market_bonus += 4
    elif strategic_material:
        product_process_bonus_tech += 10
        capability_moat_bonus += 8
        capability_market_bonus += 12
    elif grid_core_equipment:
        product_process_bonus_tech += 8
        capability_moat_bonus += 6
        capability_market_bonus += 10
    elif keyword_any(profile_text, ["国家地理标志", "有机食品", "典型代表", "传统工艺", "发酵", "窖藏", "陈酿", "质量控制", "稀缺产区"]):
        product_process_bonus_tech += 4

    keyword_bonus_tech = 0
    if keyword_any(profile_text, ["自主研发", "研发", "发明专利", "核心专利", "核心技术"]):
        keyword_bonus_tech += 4
    if keyword_any(profile_text, ["算法", "实验室", "国家级", "企业技术中心", "高新技术企业", "专精特新"]):
        keyword_bonus_tech += 2
    if keyword_any(profile_text, ["全球领先", "行业领先", "首创", "进口替代"]):
        keyword_bonus_tech += 2
    if raw["board"] in {"star_market", "chinext"}:
        keyword_bonus_tech += 1
    keyword_bonus_tech = min(keyword_bonus_tech, 7)

    business_moat = clamp(prior.business_moat + (revenue_pct - 50) * 0.10 + keyword_bonus_moat + capability_moat_bonus)
    technology_barrier = clamp(prior.technology_barrier + (rd_pct - 50) * 0.10 + keyword_bonus_tech + product_process_bonus_tech)
    if business_moat >= 90 and product_process_bonus_tech:
        technology_barrier = max(technology_barrier, 78 if baijiu_long_cycle else 72)
    market_position = clamp(45 + revenue_pct * 0.28 + profit_pct * 0.12 + (prior.business_moat - 50) * 0.25 + capability_market_bonus)
    peer_group_size = int(pct(percentiles["peer_group_size"], code))
    if peer_group_size < 10:
        market_position = min(market_position, 88)
    elif peer_group_size < 20:
        market_position = min(market_position, 94)
    business_quality = clamp(prior.business_quality + (gross_pct - 50) * 0.14 + (net_pct - 50) * 0.10 + (growth_pct - 50) * 0.08)
    operating_quality = clamp(50 + (roe_pct - 50) * 0.16 + (roic_pct - 50) * 0.14 + (cash_pct - 50) * 0.16 + (debt_safety_pct - 50) * 0.10)
    industry_outlook_score = clamp(outlook.score)
    governance_risk = clamp(72 + (debt_safety_pct - 50) * 0.06)
    comparable_leader = cross_market_leader_signal(industry_text, profile_text)
    if comparable_leader:
        technology_barrier = clamp(technology_barrier - 2)
        market_position = clamp(market_position - 2)
        governance_risk = clamp(governance_risk - 3)
        cross_market_note = "Cross-market calibration: global, scarce-resource, regulated, strategic-material, grid-equipment, or strong-brand evidence is present, so only the baseline A-share disclosure comparability discount is applied."
    else:
        business_moat = clamp(business_moat - 8)
        technology_barrier = clamp(technology_barrier - 12)
        market_position = clamp(market_position - 10)
        industry_outlook_score = clamp(industry_outlook_score - 4)
        governance_risk = clamp(governance_risk - 4)
        cross_market_note = "Cross-market calibration: no clear global, scarce-resource, regulated, or strong-brand evidence was found, so local peer leadership and promotional profile language are discounted for global comparability."

    weighted = weighted_score(
        {
            "business_moat": business_moat,
            "technology_barrier": technology_barrier,
            "market_position": market_position,
            "business_quality": business_quality,
            "operating_quality": operating_quality,
            "industry_outlook": industry_outlook_score,
            "governance_risk": governance_risk,
        }
    )

    revenue = financial.get("total_operating_revenue", "")
    net_profit = financial.get("parent_net_profit", "")
    gross_margin = financial.get("gross_margin_pct", "")
    roe = financial.get("roe_weighted_pct", "")
    rd_ratio = financial.get("research_expense_to_revenue_pct", "")
    debt_ratio = financial.get("debt_asset_ratio_pct", "")
    annual_date = financial.get("latest_annual_report_date", "")
    confidence = "high" if annual_date and profile.get("org_profile") else "medium"

    reasons = {
        "business_moat_reason": f"Peer group {peer_group}; capability-first capital replicability view: {prior.capital_replicability}; revenue peer percentile is {revenue_pct:.0f}; current profit percentile {profit_pct:.0f} is recorded but not used directly in moat scoring; leadership, brand, license, or exclusivity profile keywords add {keyword_bonus_moat} points and strategic capability adds {capability_moat_bonus} points. {cross_market_note}",
        "technology_barrier_reason": f"Technology prior from peer group plus disclosed R&D ratio percentile {rd_pct:.0f}; board and profile technology keywords add {keyword_bonus_tech} points; product/process/origin/strategic-material/grid-equipment capability adds {product_process_bonus_tech} points. {cross_market_note}",
        "market_position_reason": f"Market position uses revenue RMB {revenue} and parent net profit RMB {net_profit} relative to peer group percentiles {revenue_pct:.0f}/{profit_pct:.0f}, but current profit has lower weight in v0.4; strategic capability adds {capability_market_bonus} points; peer group size is {peer_group_size}, so narrow local peer groups are capped below global-leader scores. {cross_market_note}",
        "business_quality_reason": f"Business quality uses gross margin {gross_margin}% net margin {financial.get('net_margin_pct', '')}% and revenue growth {financial.get('revenue_yoy_pct', '')}% against peers, with lower weight than capability dimensions in v0.4.",
        "operating_quality_reason": f"Operating quality uses ROE {roe}% ROIC {financial.get('roic_pct', '')}% cash-flow-to-revenue {financial.get('cashflow_to_revenue_pct', '')}% and debt ratio {debt_ratio}%; it constrains risk but no longer dominates the watchlist score in v0.4.",
        "industry_outlook_reason": f"{outlook.reason} {cross_market_note}",
        "governance_risk_reason": f"Governance and risk score starts from public disclosure availability and adjusts for balance-sheet pressure; latest annual evidence date is {annual_date or 'not identified'}. {cross_market_note}",
    }

    base.update(
        {
            "screening_status": "scored",
            "disclosure_status": "sufficient_public_evidence",
            "peer_relative_position": peer_position(weighted),
            "cyclicality_profile": outlook.cyclicality_profile,
            "compounding_profile": outlook.compounding_profile,
            "business_moat_score": fmt_score(business_moat),
            "business_moat_level": level(business_moat),
            "business_moat_reason": reasons["business_moat_reason"],
            "technology_barrier_score": fmt_score(technology_barrier),
            "technology_barrier_level": level(technology_barrier),
            "technology_barrier_reason": reasons["technology_barrier_reason"],
            "market_position_score": fmt_score(market_position),
            "market_position_level": level(market_position),
            "market_position_reason": reasons["market_position_reason"],
            "business_quality_score": fmt_score(business_quality),
            "business_quality_level": level(business_quality),
            "business_quality_reason": reasons["business_quality_reason"],
            "operating_quality_score": fmt_score(operating_quality),
            "operating_quality_level": level(operating_quality),
            "operating_quality_reason": reasons["operating_quality_reason"],
            "industry_outlook_score": fmt_score(industry_outlook_score),
            "industry_outlook_level": level(industry_outlook_score),
            "industry_outlook_reason": reasons["industry_outlook_reason"],
            "governance_risk_score": fmt_score(governance_risk),
            "governance_risk_level": level(governance_risk),
            "governance_risk_reason": reasons["governance_risk_reason"],
            "weighted_total_score": fmt_score(weighted),
            "overall_level": level(weighted),
            "overall_reason": f"Weighted score from seven stored dimensions using the v0.4 capability-first weights, including industry outlook and cyclicality profile {outlook.cyclicality_profile}. This first-pass algorithmic score is evidence-backed by Eastmoney F10 profile and financial indicators; R&D ratio is {rd_ratio or 'not disclosed'}%.",
            "evidence_confidence": confidence,
        }
    )
    return base


def run(args: argparse.Namespace) -> tuple[int, int, int]:
    _, raw_rows = read_csv(args.raw)
    profiles = by_code(args.profiles)
    financials = by_code(args.financials)
    reviewed_at = utc_now()

    scored_financial_rows = [
        financials[row["security_code"]] | {
            "peer_group": (profiles.get(row["security_code"], {}).get("eastmoney_industry") or row.get("industry") or "unknown")
        }
        for row in raw_rows
        if financials.get(row["security_code"], {}).get("fetch_status") == "fetched"
    ]

    percentiles = {
        "total_operating_revenue": percentile_maps(scored_financial_rows, "peer_group", "total_operating_revenue"),
        "parent_net_profit": percentile_maps(scored_financial_rows, "peer_group", "parent_net_profit"),
        "gross_margin_pct": percentile_maps(scored_financial_rows, "peer_group", "gross_margin_pct"),
        "net_margin_pct": percentile_maps(scored_financial_rows, "peer_group", "net_margin_pct"),
        "roe_weighted_pct": percentile_maps(scored_financial_rows, "peer_group", "roe_weighted_pct"),
        "roic_pct": percentile_maps(scored_financial_rows, "peer_group", "roic_pct"),
        "cashflow_to_revenue_pct": percentile_maps(scored_financial_rows, "peer_group", "cashflow_to_revenue_pct"),
        "debt_asset_ratio_pct_inverse": percentile_maps(scored_financial_rows, "peer_group", "debt_asset_ratio_pct", reverse=True),
        "research_expense_to_revenue_pct": percentile_maps(scored_financial_rows, "peer_group", "research_expense_to_revenue_pct"),
        "revenue_yoy_pct": percentile_maps(scored_financial_rows, "peer_group", "revenue_yoy_pct"),
        "peer_group_size": peer_size_map(scored_financial_rows, "peer_group"),
    }

    output_rows = [
        score_row(
            raw=row,
            profile=profiles.get(row["security_code"], {}),
            financial=financials.get(row["security_code"], {}),
            percentiles=percentiles,
            reviewed_at=reviewed_at,
        )
        for row in raw_rows
    ]
    scored_count = sum(1 for row in output_rows if row["screening_status"] == "scored")
    pending_count = sum(1 for row in output_rows if row["screening_status"] == "pending_research")
    if args.require_complete and pending_count:
        raise ScoringError(f"{pending_count} A-share rows are still pending research evidence")

    write_csv(args.output, OUTPUT_COLUMNS, output_rows)
    watchlist_source_rows = [
        row
        for row in output_rows
        if row["screening_status"] == "scored" and row["weighted_total_score"] and float(row["weighted_total_score"]) >= args.candidate_threshold
    ]
    watchlist_source_rows.sort(key=lambda row: (-float(row["weighted_total_score"]), row["security_code"]))
    watchlist_rows = [watchlist_row(row) for row in watchlist_source_rows]
    write_csv(args.watchlist, WATCHLIST_COLUMNS, watchlist_rows)
    return len(output_rows), scored_count, len(watchlist_rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run A-share full-coverage dimensional moat scoring.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
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
    print(f"Wrote {total_count} A-share screening rows to {args.output}")
    print(f"Scored {scored_count} rows with fetched evidence")
    print(f"Wrote {watchlist_count} watchlist rows to {args.watchlist}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScoringError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
