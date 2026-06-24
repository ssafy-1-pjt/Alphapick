from collections import Counter
from datetime import date, datetime, time, timedelta
import json
import re

import pandas as pd
from django.db import transaction
from django.db.models import Max, Prefetch
from django.conf import settings
from django.utils import timezone
import requests

from .models import AICommentCache, FinancialMetric, PortfolioItem, PortfolioRun, PriceDaily, ScoreSnapshot, Stock


PORTFOLIO_THRESHOLD = 70
MIN_RELIABILITY_SCORE = 70
MIN_COMPONENT_SCORE = 70
PRICE_HISTORY_DAYS = 1095
PRICE_REFRESH_LOOKBACK_DAYS = PRICE_HISTORY_DAYS + 40
KRX_VOLUME_PROFILE = (
    (time(9, 0), 0.00),
    (time(9, 30), 0.12),
    (time(10, 0), 0.21),
    (time(11, 0), 0.35),
    (time(12, 0), 0.45),
    (time(13, 0), 0.55),
    (time(14, 0), 0.67),
    (time(15, 0), 0.82),
    (time(15, 30), 1.00),
)
BACKTEST_PERIODS = {
    "1w": {"days": 7, "label": "1주"},
    "1m": {"days": 30, "label": "1개월"},
    "3m": {"days": 90, "label": "3개월"},
    "1y": {"days": 365, "label": "1년"},
}
RISK_TYPE_NEUTRAL = "neutral"
RISK_TYPE_AGGRESSIVE = "aggressive"
RISK_TYPE_STABLE = "stable"
RISK_TYPES = {RISK_TYPE_AGGRESSIVE, RISK_TYPE_NEUTRAL, RISK_TYPE_STABLE}
RISK_LABELS = {
    RISK_TYPE_AGGRESSIVE: "공격형",
    RISK_TYPE_NEUTRAL: "중립형",
    RISK_TYPE_STABLE: "안정형",
}
RISK_WEIGHTS = {
    RISK_TYPE_AGGRESSIVE: {
        "company": 0.38,
        "timing": 0.62,
    },
    RISK_TYPE_NEUTRAL: {
        "company": 0.45,
        "timing": 0.55,
    },
    RISK_TYPE_STABLE: {
        "company": 0.62,
        "timing": 0.38,
    },
}
RISK_HURDLES = {
    RISK_TYPE_AGGRESSIVE: {
        "company": 65,
        "timing": 75,
        "reliability": 65,
        "sector_cap": 35,
    },
    RISK_TYPE_NEUTRAL: {
        "company": 70,
        "timing": 70,
        "reliability": 70,
        "sector_cap": 30,
    },
    RISK_TYPE_STABLE: {
        "company": 75,
        "timing": 65,
        "reliability": 75,
        "sector_cap": 25,
    },
}
CASH_POLICY_BY_RISK = {
    RISK_TYPE_AGGRESSIVE: {
        "breadth": {"strong": 0, "neutral": 10, "weak": 20, "crisis": 100},
        "market": {"strong": 0, "neutral": 10, "weak": 20, "crisis": 35},
    },
    RISK_TYPE_NEUTRAL: {
        "breadth": {"strong": 0, "neutral": 15, "weak": 30, "crisis": 100},
        "market": {"strong": 0, "neutral": 15, "weak": 30, "crisis": 50},
    },
    RISK_TYPE_STABLE: {
        "breadth": {"strong": 5, "neutral": 20, "weak": 35, "crisis": 100},
        "market": {"strong": 5, "neutral": 20, "weak": 40, "crisis": 60},
    },
}


def normalize_risk_type(value):
    value = (value or RISK_TYPE_NEUTRAL).lower()
    return value if value in RISK_TYPES else RISK_TYPE_NEUTRAL


def latest_score_date():
    return ScoreSnapshot.objects.aggregate(value=Max("base_date"))["value"]


def latest_price_date():
    return PriceDaily.objects.aggregate(value=Max("date"))["value"]


def latest_scores_queryset(base_date=None):
    base_date = base_date or latest_score_date()
    if not base_date:
        return ScoreSnapshot.objects.none()
    return (
        ScoreSnapshot.objects.filter(base_date=base_date)
        .select_related("stock")
        .order_by("-total_score", "stock__name")
    )


def portfolio_candidates(base_date=None):
    hurdles = hurdles_for_risk(RISK_TYPE_NEUTRAL)
    return latest_scores_queryset(base_date).filter(
        reliability_score__gte=hurdles["reliability"],
        company_score__gte=hurdles["company"],
        timing_score__gte=hurdles["timing"],
        stock__is_active=True,
        stock__is_tradable=True,
        stock__is_universe_included=True,
        stock__low_liquidity_flag=False,
        fail_safe_flag=False,
        stock__prices__isnull=False,
        stock__financial_metrics__isnull=False,
    ).distinct()


def watch_candidates(base_date=None, limit=5):
    hurdles = hurdles_for_risk(RISK_TYPE_NEUTRAL)
    return list(
        latest_scores_queryset(base_date)
        .filter(stock__is_active=True, stock__is_tradable=True)
        .exclude(
            reliability_score__gte=hurdles["reliability"],
            company_score__gte=hurdles["company"],
            timing_score__gte=hurdles["timing"],
            stock__low_liquidity_flag=False,
            fail_safe_flag=False,
        )[:limit]
    )


def weighted_component_score(score, risk_type=RISK_TYPE_NEUTRAL):
    risk_type = normalize_risk_type(risk_type)
    weights = RISK_WEIGHTS[risk_type]
    return round(score.company_score * weights["company"] + score.timing_score * weights["timing"], 2)


def score_for_risk(score, risk_type=RISK_TYPE_NEUTRAL):
    """Re-score by risk type while preserving the strict risk discount from the stored total."""
    if risk_type == RISK_TYPE_NEUTRAL:
        return round(score.total_score, 1)
    neutral_base = weighted_component_score(score, RISK_TYPE_NEUTRAL) or 1
    risk_discount = score.total_score / neutral_base
    adjusted_score = weighted_component_score(score, risk_type) * risk_discount
    return round(max(0, min(100, adjusted_score)), 1)


def stock_theme_links(stock):
    return list(stock.theme_links.select_related("theme__group").all())


def display_sector_for_stock(stock):
    links = stock_theme_links(stock)
    primary = next((link for link in links if link.is_primary), None) or (links[0] if links else None)
    return primary.theme.group.name if primary else stock.sector


def theme_names_for_stock(stock):
    names = []
    for link in stock_theme_links(stock):
        if link.theme.name not in names:
            names.append(link.theme.name)
    return names


def primary_theme_for_stock(stock):
    themes = theme_names_for_stock(stock)
    return themes[0] if themes else stock.primary_theme or stock.sector


def company_score_for_risk(score, risk_type=RISK_TYPE_NEUTRAL):
    return round(score.company_score, 1)


def timing_score_for_risk(score, risk_type=RISK_TYPE_NEUTRAL):
    return round(score.timing_score, 1)


def hurdles_for_risk(risk_type):
    return RISK_HURDLES[normalize_risk_type(risk_type)]


def passes_entry_hurdles(company_score, timing_score, reliability_score, risk_type):
    hurdles = hurdles_for_risk(risk_type)
    return (
        company_score >= hurdles["company"]
        and timing_score >= hurdles["timing"]
        and reliability_score >= hurdles["reliability"]
    )


def area_score_value(score, key):
    value = (score.area_scores or {}).get(key)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def average_market_direction(rows):
    values = [row["market_direction"] for row in rows if row.get("market_direction") is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def cash_policy_for(items, rows, risk_type):
    risk_type = normalize_risk_type(risk_type)
    policy = CASH_POLICY_BY_RISK[risk_type]
    pass_count = len(items)
    if pass_count == 0:
        breadth_key = "crisis"
        breadth_label = "위기장"
    elif pass_count <= 2:
        breadth_key = "weak"
        breadth_label = "약세장"
    elif pass_count <= 4:
        breadth_key = "neutral"
        breadth_label = "중립장"
    else:
        breadth_key = "strong"
        breadth_label = "강세장"
    breadth_cash = policy["breadth"][breadth_key]

    market_direction = average_market_direction(items) or average_market_direction(rows)
    if market_direction is None:
        market_cash = 0
        market_label = "시장 방향 데이터 부족"
    elif market_direction >= 65:
        market_key = "strong"
        market_label = "강세장"
    elif market_direction >= 50:
        market_key = "neutral"
        market_label = "중립장"
    elif market_direction >= 40:
        market_key = "weak"
        market_label = "약세장"
    else:
        market_key = "crisis"
        market_label = "위기장"
    if market_direction is not None:
        market_cash = policy["market"][market_key]

    cash_weight = max(breadth_cash, market_cash)
    reasons = [
        f"{RISK_LABELS[risk_type]} 편입 후보 {pass_count}개 기준 {breadth_label} 판단: 현금 {breadth_cash}%",
    ]
    if market_direction is not None:
        reasons.append(f"{RISK_LABELS[risk_type]} 시장 방향 평균 {market_direction}점 기준 {market_label} 판단: 현금 {market_cash}%")
    else:
        reasons.append("시장 방향 평균을 계산할 수 없어 편입 후보 수 기준을 우선 적용")
    return cash_weight, market_direction, market_label if market_cash >= breadth_cash else breadth_label, reasons


def sector_totals(items):
    totals = Counter()
    for row in items:
        totals[row["sector"] or "기타"] += row.get("weight", 0)
    return totals


def apply_sector_cap(items, sector_cap):
    capped_sectors = []
    sector_cash = 0
    if not items:
        return sector_cash, capped_sectors

    for row in items:
        row["sector_cap_reduction"] = 0
        row["sector_cap_applied"] = False

    totals = sector_totals(items)
    excess = 0
    for sector, total in list(totals.items()):
        if total <= sector_cap:
            continue
        overflow = total - sector_cap
        scale = sector_cap / total if total else 0
        sector_rows = [row for row in items if (row["sector"] or "기타") == sector]
        for row in sector_rows:
            original_weight = row["weight"]
            row["weight"] = original_weight * scale
            reduction = original_weight - row["weight"]
            row["sector_cap_reduction"] += reduction
            row["sector_cap_applied"] = True
        capped_sectors.append({"sector": sector, "excess": round(overflow, 2)})
        excess += overflow

    while excess > 0.01:
        totals = sector_totals(items)
        candidates = [row for row in items if totals[row["sector"] or "기타"] < sector_cap - 0.01]
        if not candidates:
            break
        basis_sum = sum(max(row["eligibility_score"] - PORTFOLIO_THRESHOLD, 1) for row in candidates)
        allocated = 0
        for row in candidates:
            sector = row["sector"] or "기타"
            capacity = max(sector_cap - totals[sector], 0)
            if capacity <= 0:
                continue
            basis = max(row["eligibility_score"] - PORTFOLIO_THRESHOLD, 1)
            proposed = excess * (basis / basis_sum) if basis_sum else excess / len(candidates)
            addition = min(proposed, capacity)
            row["weight"] += addition
            totals[sector] += addition
            allocated += addition
        if allocated <= 0.01:
            break
        excess -= allocated

    sector_cash = max(excess, 0)
    return sector_cash, capped_sectors


def sector_warning_for(scores):
    sectors = Counter(getattr(score, "sector", None) or score.stock.sector for score in scores)
    if not sectors:
        return ""
    sector, count = sectors.most_common(1)[0]
    if count >= 4:
        return f"{sector} 섹터 편입 종목이 {count}개입니다. MVP에서는 그대로 편입하지만 섹터 편중에 유의하세요."
    return ""


def build_portfolio_summary(scores):
    if not scores:
        return "오늘은 중립형 기준 회사 가치와 진입 타이밍이 모두 70점을 넘긴 종목이 없습니다. 관찰 후보를 확인하고 다음 리밸런싱을 기다려주세요."
    avg_score = sum(weighted_component_score(score) for score in scores) / len(scores)
    top_reasons = " · ".join(score.stock.name for score in scores[:3])
    return f"{len(scores)}개 종목이 중립형 기준 회사 가치 70점 이상, 진입 타이밍 70점 이상 조건을 통과했습니다. 평균 균형 점수는 {avg_score:.1f}점이며 핵심 편입 종목은 {top_reasons}입니다."


def build_dynamic_portfolio_payload(base_date=None, risk_type=RISK_TYPE_NEUTRAL):
    risk_type = normalize_risk_type(risk_type)
    hurdles = hurdles_for_risk(risk_type)
    base_date = base_date or latest_score_date() or date.today()
    scores = list(
        latest_scores_queryset(base_date)
        .filter(
            stock__is_active=True,
            stock__is_tradable=True,
            stock__is_universe_included=True,
            stock__prices__isnull=False,
            stock__financial_metrics__isnull=False,
        )
        .distinct()
    )
    rows = []
    for score in scores:
        adjusted_score = score_for_risk(score, risk_type)
        company_score = company_score_for_risk(score, risk_type)
        timing_score = timing_score_for_risk(score, risk_type)
        eligibility_score = weighted_component_score(score, risk_type)
        reliability_score = round(score.reliability_score, 1)
        passes_hurdles = passes_entry_hurdles(company_score, timing_score, reliability_score, risk_type)
        rows.append(
            {
                "score_obj": score,
                "ticker": score.stock.ticker,
                "name": score.stock.name,
                "market": score.stock.market,
                "sector": display_sector_for_stock(score.stock),
                "original_sector": score.stock.sector,
                "primary_theme": primary_theme_for_stock(score.stock),
                "themes": theme_names_for_stock(score.stock),
                "total_score": adjusted_score,
                "eligibility_score": round(eligibility_score, 1),
                "company_score": company_score,
                "timing_score": timing_score,
                "reliability_score": reliability_score,
                "passes_company_timing": passes_hurdles,
                "passes_hurdles": passes_hurdles,
                "market_direction": area_score_value(score, "marketDirection"),
                "signal": score.signal,
                "key_reason": score.key_reason or score.reason,
                "rs_rank": score.rs_rank,
                "rsi": score.rsi,
                "volume_ratio": score.volume_ratio,
                "target_upside": score.target_upside,
                "target_upside_clipped": score.target_upside_clipped,
                "consensus": score.consensus,
                "confidence": score.confidence,
                "fail_safe_flag": score.fail_safe_flag,
                "volume_surge_flag": score.volume_surge_flag,
                "low_liquidity_flag": score.stock.low_liquidity_flag,
                "reason": score.reason,
                "warning": score.warning,
            }
        )
    rows.sort(key=lambda row: (-row["passes_company_timing"], -row["eligibility_score"], -row["total_score"], row["name"]))
    items = [
        row
        for row in rows
        if row["passes_company_timing"]
        and not row["low_liquidity_flag"]
        and not row["fail_safe_flag"]
    ]
    base_cash_weight, market_direction, market_regime, cash_reasons = cash_policy_for(items, rows, risk_type)
    equity_budget = max(100 - base_cash_weight, 0)
    score_sum = sum(max(row["eligibility_score"] - PORTFOLIO_THRESHOLD, 1) for row in items)
    for row in items:
        score_edge = max(row["eligibility_score"] - PORTFOLIO_THRESHOLD, 1)
        row["raw_weight"] = (score_edge / score_sum) * equity_budget if score_sum else 0
        row["weight"] = row["raw_weight"]

    sector_cash_weight, capped_sectors = apply_sector_cap(items, hurdles["sector_cap"])
    stock_weight_sum = sum(row["weight"] for row in items)
    cash_weight = max(0, 100 - stock_weight_sum)
    sector_cash_weight = max(0, cash_weight - base_cash_weight)
    if sector_cash_weight > 0.01:
        cash_reasons.append(f"섹터 Cap 재분배 불가 비중 {sector_cash_weight:.1f}%를 현금으로 전환")

    for row in items:
        row["raw_weight"] = round(row.get("raw_weight", 0), 2)
        row["weight"] = round(row["weight"], 2)
        row["sector_cap_reduction"] = round(row.get("sector_cap_reduction", 0), 2)

    base_cash_weight = round(base_cash_weight, 2)
    cash_weight = round(max(0, 100 - sum(row["weight"] for row in items)), 2)
    sector_cash_weight = round(max(0, cash_weight - base_cash_weight), 2)
    item_tickers = {row["ticker"] for row in items}
    watch_rows = [row for row in rows if row["ticker"] not in item_tickers][:5]
    watch_candidates_payload = [
        {
            "ticker": row["ticker"],
            "name": row["name"],
            "market": row["market"],
            "sector": row["sector"],
            "original_sector": row["original_sector"],
            "primary_theme": row["primary_theme"],
            "themes": row["themes"],
            "industry": row["score_obj"].stock.industry,
            "latest_score": row["total_score"],
            "signal": row["signal"],
            "key_reason": row["key_reason"],
            "low_liquidity_flag": row["low_liquidity_flag"],
            "fail_safe_flag": row["fail_safe_flag"],
            "volume_surge_flag": row["volume_surge_flag"],
            "current_price": row["score_obj"].stock.financial_metrics.first().current_price
            if row["score_obj"].stock.financial_metrics.first()
            else None,
            "reason": row["reason"],
        }
        for row in watch_rows
    ]
    allocation_items = [
        {
            "type": "stock",
            "ticker": row["ticker"],
            "name": row["name"],
            "sector": row["sector"],
            "themes": row["themes"],
            "weight": row["weight"],
        }
        for row in items
    ]
    if cash_weight > 0:
        allocation_items.append(
            {
                "type": "cash",
                "ticker": "CASH",
                "name": "현금",
                "sector": "현금",
                "weight": cash_weight,
            }
        )
    item_payload = []
    for row in items:
        clean_row = row.copy()
        clean_row.pop("score_obj", None)
        clean_row.pop("market_direction", None)
        item_payload.append(clean_row)
    portfolio_score = round(sum(row["total_score"] for row in items) / len(items), 2) if items else 0
    eligibility_average = round(sum(row["eligibility_score"] for row in items) / len(items), 2) if items else 0
    sector_messages = [
        f"{item['sector']} 섹터가 최대 {hurdles['sector_cap']}%를 초과해 {item['excess']}%를 재배분했습니다."
        for item in capped_sectors
    ]
    sector_warning = " ".join(sector_messages)
    if not items:
        summary = f"{RISK_LABELS[risk_type]} 기준 편입 허들을 통과한 종목이 없어 주식 비중을 0%로 두고 현금 100%를 권장합니다. 관찰 후보 TOP 5를 확인하세요."
    else:
        names = " · ".join(row["name"] for row in items[:3])
        summary = (
            f"{RISK_LABELS[risk_type]} 기준 {len(items)}개 종목이 편입 허들을 통과했습니다. "
            f"평균 균형 점수는 {eligibility_average:.1f}점이며 핵심 편입 종목은 {names}입니다. "
            f"시장/분산 리스크를 반영해 현금 {cash_weight:.1f}%를 함께 권장합니다."
        )
    return {
        "baseDate": base_date.isoformat(),
        "portfolioScore": portfolio_score,
        "eligibilityScore": eligibility_average,
        "rebalanceType": "daily",
        "threshold": PORTFOLIO_THRESHOLD,
        "companyTimingThreshold": MIN_COMPONENT_SCORE,
        "hurdles": {
            "company": hurdles["company"],
            "timing": hurdles["timing"],
            "reliability": hurdles["reliability"],
        },
        "sectorCap": hurdles["sector_cap"],
        "cashWeight": cash_weight,
        "baseCashWeight": base_cash_weight,
        "sectorCashWeight": sector_cash_weight,
        "cashReasons": cash_reasons,
        "marketDirectionScore": market_direction,
        "marketRegime": market_regime,
        "allocationItems": allocation_items,
        "userRiskType": risk_type,
        "riskTypeLabel": RISK_LABELS[risk_type],
        "summary": summary,
        "sectorWarning": sector_warning,
        "items": item_payload,
        "watchCandidates": watch_candidates_payload,
        "benchmarkSummary": {
            "benchmark": "KOSPI",
            "rebalanceType": "daily",
            "threshold": PORTFOLIO_THRESHOLD,
            "companyTimingThreshold": MIN_COMPONENT_SCORE,
            "itemCount": len(items),
            "cashWeight": cash_weight,
            "message": "성향별 회사/타이밍 허들과 현금 비중, 섹터 Cap을 반영한 백테스트 요약은 /api/portfolio/backtest/에서 제공합니다.",
        },
    }


@transaction.atomic
def ensure_portfolio_run(base_date=None):
    base_date = base_date or latest_score_date() or date.today()
    payload = build_dynamic_portfolio_payload(base_date=base_date, risk_type=RISK_TYPE_NEUTRAL)
    scores = {
        score.stock_id: score
        for score in ScoreSnapshot.objects.filter(base_date=base_date).select_related("stock")
    }

    run, _ = PortfolioRun.objects.update_or_create(
        base_date=base_date,
        defaults={
            "threshold": PORTFOLIO_THRESHOLD,
            "rebalance_type": "daily",
            "portfolio_score": payload["portfolioScore"],
            "summary": payload["summary"],
            "sector_warning": payload["sectorWarning"],
        },
    )
    run.items.all().delete()

    for item in payload["items"]:
        score = scores.get(item["ticker"])
        if not score:
            continue
        PortfolioItem.objects.create(
            portfolio_run=run,
            stock=score.stock,
            score_snapshot=score,
            score=score.total_score,
            weight=item["weight"],
            reason=score.reason,
            warning=score.warning,
        )
    return run


def get_today_portfolio():
    base_date = latest_score_date()
    if not base_date:
        return None
    return ensure_portfolio_run(base_date)


def portfolio_history(limit=20):
    return PortfolioRun.objects.prefetch_related(
        Prefetch("items", queryset=PortfolioItem.objects.select_related("stock", "score_snapshot"))
    ).order_by("-base_date")[:limit]


def stock_report(ticker):
    score_date = latest_score_date()
    stock = Stock.objects.prefetch_related("theme_links__theme__group").get(ticker=ticker)
    refresh_price_history_from_pykrx(stock)
    score = stock.scores.filter(base_date=score_date).first() or stock.scores.first()
    metric = stock.financial_metrics.order_by("-base_date").first()
    prices = list(stock.prices.order_by("-date")[:PRICE_HISTORY_DAYS])
    prices.reverse()
    return {
        "stock": stock,
        "score": score,
        "metric": metric,
        "prices": prices,
        "refreshed_at": timezone.localtime(),
    }


def refresh_price_history_from_pykrx(stock):
    """Best-effort daily OHLCV refresh for report pages.

    The app stores EOD-style data locally, but same-day pykrx rows can change
    after an earlier intraday seed. Refreshing only the viewed ticker prevents
    obviously stale current price and volume displays without blocking the UI
    when pykrx is unavailable.
    """
    try:
        from pykrx import stock as krx_stock
    except Exception:
        return False

    code = stock.ticker.split(".")[0]
    end_date = date.today()
    start_date = end_date - timedelta(days=PRICE_REFRESH_LOOKBACK_DAYS)

    try:
        raw = krx_stock.get_market_ohlcv_by_date(
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            code,
        )
    except Exception:
        return False

    frame = normalize_pykrx_ohlcv(raw)
    if frame.empty:
        return False

    latest = frame.iloc[-1]
    latest_date = frame.index[-1].date()
    saved = stock.prices.order_by("-date").first()
    if (
        saved
        and saved.date == latest_date
        and saved.close_price == int(latest["close"])
        and saved.volume == int(latest["volume"])
    ):
        return False

    save_refreshed_prices(stock, frame.tail(PRICE_HISTORY_DAYS))
    metric = FinancialMetric.objects.filter(stock=stock).order_by("-base_date").first()
    if metric:
        metric.current_price = int(latest["close"])
        metric.save(update_fields=["current_price"])
    update_refreshed_volume_score(stock, frame)
    return True


def normalize_pykrx_ohlcv(raw):
    if raw.empty:
        return pd.DataFrame()

    frame = raw.copy()
    column_map = {
        "시가": "open",
        "고가": "high",
        "저가": "low",
        "종가": "close",
        "거래량": "volume",
    }
    frame = frame.rename(columns=column_map)
    required = ["open", "high", "low", "close", "volume"]
    if not all(column in frame.columns for column in required):
        return pd.DataFrame()

    frame = frame[required].dropna()
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna()
    frame = frame[(frame["open"] > 0) & (frame["high"] > 0) & (frame["low"] > 0) & (frame["close"] > 0)]
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()
    close = frame["close"]
    frame["ema20"] = close.ewm(span=20, adjust=False).mean()
    frame["ema50"] = close.ewm(span=50, adjust=False).mean()
    frame["ema200"] = close.ewm(span=200, adjust=False).mean()
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    frame["bb_upper"] = ma20 + std20 * 2
    frame["bb_lower"] = ma20 - std20 * 2
    direction = close.diff().fillna(0).apply(lambda value: 1 if value > 0 else -1 if value < 0 else 0)
    frame["obv"] = (direction * frame["volume"]).cumsum()
    return frame


@transaction.atomic
def save_refreshed_prices(stock, frame):
    start = frame.index[0].date()
    PriceDaily.objects.filter(stock=stock, date__gte=start).delete()
    PriceDaily.objects.bulk_create(
        [
            PriceDaily(
                stock=stock,
                date=row_date.date(),
                open_price=int(row["open"]),
                high_price=int(row["high"]),
                low_price=int(row["low"]),
                close_price=int(row["close"]),
                volume=int(row["volume"]),
                ema20=None if pd.isna(row["ema20"]) else float(row["ema20"]),
                ema50=None if pd.isna(row["ema50"]) else float(row["ema50"]),
                ema200=None if pd.isna(row["ema200"]) else float(row["ema200"]),
                bb_upper=None if pd.isna(row["bb_upper"]) else float(row["bb_upper"]),
                bb_lower=None if pd.isna(row["bb_lower"]) else float(row["bb_lower"]),
                obv=None if pd.isna(row["obv"]) else float(row["obv"]),
            )
            for row_date, row in frame.iterrows()
        ],
        batch_size=1000,
    )


def update_refreshed_volume_score(stock, frame):
    latest_score = ScoreSnapshot.objects.filter(stock=stock).order_by("-base_date").first()
    if not latest_score:
        return

    recent_volume = frame["volume"].iloc[-21:-1].tail(20)
    average_volume = float(recent_volume.mean()) if not recent_volume.empty else 0
    latest_volume = float(frame["volume"].iloc[-1])
    projected_volume = latest_volume / market_cumulative_volume_ratio(frame.index[-1].date())
    volume_ratio = round(projected_volume / average_volume, 2) if average_volume else 1.0
    volume_surge = volume_ratio >= 2.0
    latest_score.volume_ratio = volume_ratio
    latest_score.volume_surge_flag = volume_surge

    indicators = list(latest_score.technical_indicators or [])
    for indicator in indicators:
        if indicator.get("label") == "거래량 배율":
            indicator["value"] = volume_ratio
            indicator["status"] = "급증" if volume_surge else "보통"
            break
    latest_score.technical_indicators = indicators
    latest_score.save(update_fields=["volume_ratio", "volume_surge_flag", "technical_indicators"])


def market_cumulative_volume_ratio(trade_date):
    """Return expected regular-session cumulative volume ratio for same-day rows."""
    now = timezone.localtime()
    if trade_date != now.date():
        return 1.0

    points = [
        (timezone.make_aware(datetime.combine(now.date(), point_time), now.tzinfo), ratio)
        for point_time, ratio in KRX_VOLUME_PROFILE
    ]
    if now <= points[0][0]:
        return 0.08
    if now >= points[-1][0]:
        return 1.0

    for (start_time, start_ratio), (end_time, end_ratio) in zip(points, points[1:]):
        if start_time <= now <= end_time:
            elapsed = (now - start_time).total_seconds()
            duration = (end_time - start_time).total_seconds()
            progress = elapsed / duration if duration else 0
            ratio = start_ratio + (end_ratio - start_ratio) * progress
            return max(0.08, min(1.0, ratio))

    return 1.0


def normalize_backtest_period(value):
    return value if value in BACKTEST_PERIODS else "1y"


def normalize_value_series(rows):
    rows = [(row_date, value) for row_date, value in rows if value]
    if len(rows) < 2:
        return []
    start_value = rows[0][1]
    if not start_value:
        return []
    return [{"date": row_date, "value": round((value / start_value) * 100, 4)} for row_date, value in rows]


def portfolio_price_series(items, start_date, end_date):
    weighted_stocks = []
    for item in items:
        prices = list(
            PriceDaily.objects.filter(
                stock_id=item["ticker"],
                date__gte=start_date,
                date__lte=end_date,
            )
            .order_by("date")
            .values_list("date", "close_price")
        )
        if len(prices) < 2:
            continue
        start_price = prices[0][1]
        if not start_price:
            continue
        weighted_stocks.append(
            {
                "ticker": item["ticker"],
                "weight": float(item.get("weight") or 0),
                "start_price": float(start_price),
                "prices": {row_date: float(close) for row_date, close in prices},
                "last_price": float(start_price),
            }
        )

    total_weight = sum(stock["weight"] for stock in weighted_stocks)
    if not weighted_stocks or total_weight <= 0:
        return []
    cash_weight = max(0, 100 - total_weight)

    dates = sorted({row_date for stock in weighted_stocks for row_date in stock["prices"]})
    series = []
    for row_date in dates:
        portfolio_value = cash_weight
        for stock in weighted_stocks:
            if row_date in stock["prices"]:
                stock["last_price"] = stock["prices"][row_date]
            if stock["last_price"]:
                portfolio_value += stock["weight"] * (stock["last_price"] / stock["start_price"])
        series.append({"date": row_date, "value": round(portfolio_value, 4)})
    return series


def market_proxy_benchmark_series(start_date, end_date):
    rows = list(
        PriceDaily.objects.filter(
            stock__market="KOSPI",
            stock__is_active=True,
            date__gte=start_date,
            date__lte=end_date,
        )
        .order_by("stock_id", "date")
        .values_list("stock_id", "date", "close_price")
    )
    start_prices = {}
    by_date = {}
    for ticker, row_date, close in rows:
        if not close:
            continue
        start_prices.setdefault(ticker, float(close))
        by_date.setdefault(row_date, []).append(float(close) / start_prices[ticker])
    averaged = [(row_date, (sum(values) / len(values)) * 100) for row_date, values in sorted(by_date.items()) if values]
    return [{"date": row_date, "value": round(value, 4)} for row_date, value in averaged]


def kospi_benchmark_series(start_date, end_date):
    if Stock.objects.filter(market="KOSPI").count() < 100:
        return [], "KOSPI 대용 지수"
    try:
        from pykrx import stock as krx_stock

        frame = krx_stock.get_index_ohlcv_by_date(
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            "1001",
        )
        if frame.empty:
            return [], "KOSPI 대용 지수"
        close_column = "종가" if "종가" in frame.columns else frame.columns[3]
        rows = [(index.date(), float(row[close_column])) for index, row in frame.iterrows()]
        return normalize_value_series(rows), "KOSPI"
    except Exception:
        return [], "KOSPI 대용 지수"


def align_backtest_series(portfolio_series, benchmark_series, item_count):
    if not portfolio_series:
        return [], 0, 0
    benchmark_by_date = {row["date"]: row["value"] for row in benchmark_series}
    benchmark_dates = sorted(benchmark_by_date)
    last_benchmark = benchmark_series[0]["value"] if benchmark_series else 100
    rows = []
    previous_portfolio = None
    previous_benchmark = None
    wins = 0
    comparable_days = 0
    peak = portfolio_series[0]["value"]
    max_drawdown = 0

    for point in portfolio_series:
        row_date = point["date"]
        if row_date in benchmark_by_date:
            last_benchmark = benchmark_by_date[row_date]
        elif benchmark_dates:
            for benchmark_date in benchmark_dates:
                if benchmark_date <= row_date:
                    last_benchmark = benchmark_by_date[benchmark_date]
                else:
                    break
        portfolio_value = point["value"]
        peak = max(peak, portfolio_value)
        max_drawdown = min(max_drawdown, (portfolio_value - peak) / peak * 100)
        portfolio_daily = 0 if previous_portfolio is None else (portfolio_value / previous_portfolio - 1) * 100
        benchmark_daily = 0 if previous_benchmark is None else (last_benchmark / previous_benchmark - 1) * 100
        if previous_portfolio is not None and previous_benchmark is not None:
            comparable_days += 1
            wins += int(portfolio_daily > benchmark_daily)
        rows.append(
            {
                "date": row_date.isoformat(),
                "portfolio": round(portfolio_value, 2),
                "benchmark": round(last_benchmark, 2),
                "portfolioReturn": round(portfolio_value - 100, 2),
                "benchmarkReturn": round(last_benchmark - 100, 2),
                "alpha": round((portfolio_value - last_benchmark), 2),
                "portfolioDailyReturn": round(portfolio_daily, 2),
                "benchmarkDailyReturn": round(benchmark_daily, 2),
                "itemCount": item_count,
            }
        )
        previous_portfolio = portfolio_value
        previous_benchmark = last_benchmark
    win_rate = round((wins / comparable_days) * 100, 1) if comparable_days else 0
    return rows, win_rate, round(max_drawdown, 2)


def calculate_backtest(benchmark="KOSPI", period="1y", risk_type=RISK_TYPE_NEUTRAL):
    period = normalize_backtest_period(period)
    risk_type = normalize_risk_type(risk_type)
    end_date = latest_price_date() or latest_score_date() or date.today()
    start_date = end_date - timedelta(days=BACKTEST_PERIODS[period]["days"])
    portfolio_payload = build_dynamic_portfolio_payload(risk_type=risk_type)
    items = portfolio_payload.get("items", [])
    cash_weight = portfolio_payload.get("cashWeight", 0)
    if not items:
        return {
            "benchmark": benchmark,
            "benchmarkSource": benchmark,
            "period": period,
            "periodLabel": BACKTEST_PERIODS[period]["label"],
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "rebalanceType": "daily",
            "portfolioReturn": 0,
            "benchmarkReturn": 0,
            "winRate": 0,
            "maxDrawdown": 0,
            "series": [],
            "summary": "아직 생성된 포트폴리오가 없습니다.",
        }

    portfolio_series = portfolio_price_series(items, start_date, end_date)
    benchmark_series, benchmark_source = kospi_benchmark_series(start_date, end_date)
    if not benchmark_series:
        benchmark_series = market_proxy_benchmark_series(start_date, end_date)
    series, win_rate, max_drawdown = align_backtest_series(portfolio_series, benchmark_series, len(items))
    portfolio_return = series[-1]["portfolioReturn"] if series else 0
    benchmark_return = series[-1]["benchmarkReturn"] if series else 0
    alpha = round(portfolio_return - benchmark_return, 2)

    return {
        "benchmark": benchmark.upper(),
        "benchmarkSource": benchmark_source,
        "period": period,
        "periodLabel": BACKTEST_PERIODS[period]["label"],
        "startDate": series[0]["date"] if series else start_date.isoformat(),
        "endDate": series[-1]["date"] if series else end_date.isoformat(),
        "rebalanceType": "period-hold",
        "portfolioReturn": round(portfolio_return, 2),
        "benchmarkReturn": round(benchmark_return, 2),
        "alpha": alpha,
        "winRate": win_rate,
        "maxDrawdown": max_drawdown,
        "itemCount": len(items),
        "cashWeight": cash_weight,
        "series": series,
        "summary": f"현재 {RISK_LABELS[risk_type]} 추천 포트폴리오를 {BACKTEST_PERIODS[period]['label']} 전 매수해 보유했다고 가정한 수익률입니다. 현금 {cash_weight}%는 가격 변동 없이 보유한 것으로 계산합니다.",
    }


def generate_ai_comment(ticker, risk_type=RISK_TYPE_NEUTRAL):
    risk_type = normalize_risk_type(risk_type)
    report = stock_report(ticker)
    stock = report["stock"]
    score = report["score"]
    metric = report["metric"]
    if not score:
        raise ValueError("score report is not ready")

    cached = AICommentCache.objects.filter(
        stock=stock,
        base_date=score.base_date,
        risk_type=risk_type,
    ).first()
    if cached and cached.provider == ai_comment_provider():
        return cached, True

    local_payload = build_local_ai_comment_payload(stock, score, metric, risk_type)
    gms_payload = request_gms_ai_comment(stock, score, metric, risk_type, local_payload)
    payload = gms_payload or local_payload

    comment, _ = AICommentCache.objects.update_or_create(
        stock=stock,
        base_date=score.base_date,
        risk_type=risk_type,
        defaults=payload,
    )
    return comment, False


def ai_comment_provider():
    """Return the provider expected for a newly generated AI comment.

    The version suffix deliberately invalidates the old cache: older local
    fallback comments were stored with a GMS provider name, so they never
    retried the real model after the key became available.
    """
    return f"gms-{settings.GMS_CHAT_MODEL}-meme-v7" if getattr(settings, "GMS_API_KEY", "") else "local-meme-v2"


def build_local_ai_comment_payload(stock, score, metric, risk_type):
    company = float(score.company_score or 0)
    market = market_meme_score(score)
    timing = float(score.timing_score or 0)
    action = score.action_label or score.verdict or "평가 보류"
    valuation_heavy = float(score.valuation_adjustment or 0) < 0
    warning = score.warning or ""
    action_detail = meme_action_detail(action, warning)

    if score.fail_safe_flag or score.is_investment_ineligible or stock.low_liquidity_flag:
        positive = "농담보다 리스크 관리"
        negative = strongest_meme_detail(score)
        conclusion = f"{action} · {warning or '경고 신호 먼저 확인'}"
    elif timing <= 0:
        positive = "풀매수 버튼 완전 압수"
        negative = strongest_meme_detail(score)
        conclusion = f"{action} · 타이밍 0점이라 진입각 실종"
    elif company >= 70 and timing >= 70 and ("낙폭" in warning or "과열" in warning):
        positive = "로켓은 발사, 추격은 멀미각"
        negative = f"퀄리티 {company:.1f}점, 본체는 국밥"
        conclusion = f"{action} · {action_detail}"
    elif company >= 70 and timing < 60:
        positive = "로켓은 발사, 지금 타면 멀미각" if "낙폭" in warning else "본체는 국밥, 진입각은 품절"
        negative = f"퀄리티 {company:.1f}점, 본체 체력 확실"
        conclusion = f"{action} · 타이밍 {timing:.1f}점이라 추격매수 조심"
    elif market >= 70 and company < 60:
        positive = "차트는 황제주, 본체는 점검 중"
        negative = f"시장 {market:.1f}점, 떡상 폼 확인"
        conclusion = f"{action} · 퀄리티 {company:.1f}점이라 장기 존버는 보류"
    elif company >= 70 and market >= 70 and timing >= 70:
        positive = "풀세팅인데 매수버튼 압수" if "관망" in action else "본체·차트·타점 전부 로그인"
        negative = "회사와 시장 점수 모두 상위권"
        conclusion = f"{action} · {action_detail}"
    elif valuation_heavy:
        positive = "본체는 국밥, 가격은 파인다이닝"
        negative = strongest_meme_detail(score)
        conclusion = f"{action} · {weakest_meme_detail(score)}"
    else:
        positive = "가즈아 전에 타이밍 확인"
        negative = strongest_meme_detail(score)
        conclusion = f"{action} · {weakest_meme_detail(score)}"
    return {
        "positive": positive,
        "negative": negative,
        "conclusion": conclusion,
        # A fallback must never masquerade as a successful GMS response.
        "provider": "local-meme-v2",
    }


def meme_score_rows(score):
    return [
        ("퀄리티", float(score.company_score or 0), "본체는 국밥", "본체 체력 점검"),
        ("시장", market_meme_score(score), "시장 반응 로그인", "시장 반응 로그아웃"),
        ("타이밍", float(score.timing_score or 0), "진입각 살아있음", "진입각 품절"),
    ]


def market_meme_score(score):
    v4 = (score.area_scores or {}).get("v4") or {}
    return float(score.market_validation_score or v4.get("marketValidation") or score.reliability_score or 0)


def strongest_meme_detail(score):
    label, value, strong, _ = max(meme_score_rows(score), key=lambda row: row[1])
    return f"{label} {value:.1f}점, {strong}"


def weakest_meme_detail(score):
    label, value, _, weak = min(meme_score_rows(score), key=lambda row: row[1])
    return f"{label} {value:.1f}점, {weak}"


def meme_action_detail(action, warning):
    if "관망" in action:
        if "낙폭" in warning or "과열" in warning:
            return "폼은 좋은데 변동성 커서 신규 탑승은 대기"
        return "점수는 좋아도 신호 확인 전 풀매수는 보류"
    if "익절" in action:
        return "수익 구간이면 일부 익절각부터 점검"
    if "매수" in action:
        return "분할 탑승만 검토, 몰빵은 금지"
    if "회피" in action or "제외" in action:
        return "리스크가 앞서서 손가락 대기"
    return "점수보다 리스크 확인이 먼저"


def request_gms_ai_comment(stock, score, metric, risk_type, fallback_payload):
    api_key = getattr(settings, "GMS_API_KEY", "")
    if not api_key:
        return None

    prompt_payload = {
        "stock": {
            "name": stock.name,
            "ticker": stock.ticker,
            "sector": stock.sector,
            "market": stock.market,
        },
        "riskType": RISK_LABELS[risk_type],
        "score": {
            "total": score.total_score,
            "company": score.company_score,
            "marketValidation": score.market_validation_score,
            "timing": score.timing_score,
            "valuationAdjustment": score.valuation_adjustment,
            "reliability": score.reliability_score,
            "actionSignal": score.action_signal,
            "actionLabel": score.action_label,
            "verdict": score.verdict,
            "signal": score.signal,
            "warning": score.warning,
            "reason": score.reason,
            "keyReason": score.key_reason,
            "summaryMetrics": score.summary_metrics,
            "scoreCards": score.score_cards,
            "redFlagReasons": score.red_flag_reasons,
        },
        "financial": {
            "currentPrice": metric.current_price if metric else None,
            "targetPrice": metric.target_price if metric else None,
            "per": metric.per if metric else None,
            "pbr": metric.pbr if metric else None,
            "roe": metric.roe if metric else None,
        },
        "fallbackExample": {
            "positive": fallback_payload["positive"],
            "negative": fallback_payload["negative"],
            "conclusion": fallback_payload["conclusion"],
        },
    }
    messages = [
        {
            "role": "developer",
            "content": (
                "당신은 AlphaPick의 주식 밈 카피라이터다. 입력 점수와 actionLabel을 바꾸지 말고 "
                "한국 주식 커뮤니티·유튜브 쇼츠·SNS 스타일의 짧고 강한 코멘트로 변환한다. "
                "반드시 JSON만 반환한다: {\"headline\":\"강한 주식 밈 한 줄\",\"details\":[\"강점 요약\",\"약점 요약\",\"행동 요약\"]}. "
                "headline은 8~26자, 종목명 반복과 마침표 금지. details는 정확히 3줄. "
                "headline은 actionLabel을 그대로 옮기면 실패다. '관망', '주도주', 'RS' 같은 라벨만 나열하지 말고 "
                "반드시 은어/밈 표현과 반전을 넣어라. 예: 풀매수 버튼 압수, 본체는 국밥, 진입각 품절. "
                "떡상, 존버, 풀매수, 몰빵, 가즈아, 로켓 발사 같은 표현은 비유로만 쓰고 "
                "수익 보장, 반드시 오른다, 무조건 매수, 지금 사야 함, 상한가 확정은 금지한다."
            ),
        },
        {
            "role": "user",
            "content": (
                "다음 종목 리포트 데이터를 바탕으로 가장 높은 점수와 낮은 점수의 대비를 살려 작성하세요. "
                "행동 요약에는 actionLabel을 그대로 반영하세요.\n"
                f"{json.dumps(prompt_payload, ensure_ascii=False)}"
            ),
        },
    ]
    try:
        response = requests.post(
            settings.GMS_CHAT_COMPLETIONS_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": settings.GMS_CHAT_MODEL,
                "messages": messages,
                "temperature": 0.85,
                "response_format": {"type": "json_object"},
            },
            timeout=settings.GMS_CHAT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = parse_ai_comment_json(content)
    except (KeyError, ValueError, requests.RequestException, json.JSONDecodeError):
        return None

    if not parsed or is_bad_meme_comment(parsed, stock):
        return None
    return {
        "positive": parsed["positive"],
        "negative": parsed["negative"],
        "conclusion": parsed["conclusion"],
        "provider": ai_comment_provider(),
    }


def parse_ai_comment_json(content):
    text = str(content or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    data = json.loads(text)
    if data.get("headline") and isinstance(data.get("details"), list) and len(data["details"]) >= 3:
        return {
            "positive": str(data["headline"]).strip(),
            "negative": str(data["details"][0]).strip(),
            "conclusion": " · ".join(str(item).strip() for item in data["details"][1:3] if str(item).strip()),
        }
    required = ["positive", "negative", "conclusion"]
    if not all(data.get(key) for key in required):
        return None
    return {key: str(data[key]).strip() for key in required}


def is_bad_meme_comment(payload, stock):
    headline = payload.get("positive", "")
    text = " ".join(str(value) for value in payload.values())
    meme_terms = ["떡상", "존버", "풀매수", "몰빵", "가즈아", "로켓", "국밥", "진입각", "탑승", "품절", "로그인", "압수", "우주", "멀미", "파인다이닝"]
    banned_leaks = ["actionLabel", "RS ", "RS", stock.name]
    return any(term in headline for term in banned_leaks) or "반영:" in text or not any(term in headline for term in meme_terms)
