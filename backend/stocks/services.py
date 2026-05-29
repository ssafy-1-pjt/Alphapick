from collections import Counter
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Max, Prefetch

from .models import AICommentCache, PortfolioItem, PortfolioRun, PriceDaily, ScoreSnapshot, Stock


PORTFOLIO_THRESHOLD = 70
MIN_RELIABILITY_SCORE = 70
MIN_COMPONENT_SCORE = 60
PRICE_HISTORY_DAYS = 365
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
    return latest_scores_queryset(base_date).filter(
        reliability_score__gte=MIN_RELIABILITY_SCORE,
        company_score__gte=MIN_COMPONENT_SCORE,
        timing_score__gte=MIN_COMPONENT_SCORE,
        stock__is_active=True,
        stock__is_tradable=True,
        stock__is_universe_included=True,
        stock__low_liquidity_flag=False,
        fail_safe_flag=False,
        stock__prices__isnull=False,
        stock__financial_metrics__isnull=False,
    ).distinct()


def watch_candidates(base_date=None, limit=5):
    return list(
        latest_scores_queryset(base_date)
        .filter(stock__is_active=True, stock__is_tradable=True)
        .exclude(
            reliability_score__gte=MIN_RELIABILITY_SCORE,
            company_score__gte=MIN_COMPONENT_SCORE,
            timing_score__gte=MIN_COMPONENT_SCORE,
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


def company_score_for_risk(score, risk_type=RISK_TYPE_NEUTRAL):
    return round(score.company_score, 1)


def timing_score_for_risk(score, risk_type=RISK_TYPE_NEUTRAL):
    return round(score.timing_score, 1)


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
        return "오늘은 회사 가치와 진입 타이밍이 모두 70점을 넘긴 종목이 없습니다. 관찰 후보를 확인하고 다음 리밸런싱을 기다려주세요."
    avg_score = sum(weighted_component_score(score) for score in scores) / len(scores)
    top_reasons = " · ".join(score.stock.name for score in scores[:3])
    return f"{len(scores)}개 종목이 회사 가치 70점 이상, 진입 타이밍 70점 이상 조건을 통과했습니다. 평균 균형 점수는 {avg_score:.1f}점이며 핵심 편입 종목은 {top_reasons}입니다."


def build_dynamic_portfolio_payload(base_date=None, risk_type=RISK_TYPE_NEUTRAL):
    risk_type = normalize_risk_type(risk_type)
    base_date = base_date or latest_score_date() or date.today()
    scores = list(
        latest_scores_queryset(base_date)
        .filter(
            reliability_score__gte=MIN_RELIABILITY_SCORE,
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
        rows.append(
            {
                "score_obj": score,
                "ticker": score.stock.ticker,
                "name": score.stock.name,
                "market": score.stock.market,
                "sector": score.stock.sector,
                "primary_theme": score.stock.primary_theme or score.stock.sector,
                "total_score": adjusted_score,
                "eligibility_score": round(eligibility_score, 1),
                "company_score": company_score,
                "timing_score": timing_score,
                "reliability_score": round(score.reliability_score, 1),
                "passes_company_timing": company_score >= MIN_COMPONENT_SCORE and timing_score >= MIN_COMPONENT_SCORE,
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
    score_sum = sum(max(row["total_score"] - PORTFOLIO_THRESHOLD, 0) for row in items)
    for row in items:
        if score_sum > 0:
            score_edge = max(row["total_score"] - PORTFOLIO_THRESHOLD, 0)
            row["weight"] = round((score_edge / score_sum) * 100, 2)
        else:
            row["weight"] = round(100.0 / len(items), 2) if items else 0
    item_tickers = {row["ticker"] for row in items}
    watch_rows = [row for row in rows if row["ticker"] not in item_tickers][:5]
    watch_candidates_payload = [
        {
            "ticker": row["ticker"],
            "name": row["name"],
            "market": row["market"],
            "sector": row["sector"],
            "primary_theme": row["primary_theme"],
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
    item_payload = []
    for row in items:
        clean_row = row.copy()
        clean_row.pop("score_obj", None)
        item_payload.append(clean_row)
    portfolio_score = round(sum(row["total_score"] for row in items) / len(items), 2) if items else 0
    eligibility_average = round(sum(row["eligibility_score"] for row in items) / len(items), 2) if items else 0
    sector_warning = sector_warning_for([type("PortfolioSector", (), row) for row in items])
    if not items:
        summary = f"{RISK_LABELS[risk_type]} 기준 회사 가치와 진입 타이밍이 모두 70점을 넘긴 종목이 없습니다. 관찰 후보 TOP 5를 확인하세요."
    else:
        names = " · ".join(row["name"] for row in items[:3])
        summary = f"{RISK_LABELS[risk_type]} 기준 {len(items)}개 종목이 회사 가치 70점 이상, 진입 타이밍 70점 이상 조건을 통과했습니다. 평균 균형 점수는 {eligibility_average:.1f}점이며 핵심 편입 종목은 {names}입니다."
    return {
        "baseDate": base_date.isoformat(),
        "portfolioScore": portfolio_score,
        "eligibilityScore": eligibility_average,
        "rebalanceType": "daily",
        "threshold": PORTFOLIO_THRESHOLD,
        "companyTimingThreshold": MIN_COMPONENT_SCORE,
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
            "message": "회사 가치와 진입 타이밍이 모두 70점 이상인 종목을 편입한 MVP 백테스트 요약은 /api/portfolio/backtest/에서 제공합니다.",
        },
    }


@transaction.atomic
def ensure_portfolio_run(base_date=None):
    base_date = base_date or latest_score_date() or date.today()
    scores = list(portfolio_candidates(base_date))
    score_sum = sum(max(score.total_score - PORTFOLIO_THRESHOLD, 0) for score in scores)
    portfolio_score = round(sum(score.total_score for score in scores) / len(scores), 2) if scores else 0

    run, _ = PortfolioRun.objects.update_or_create(
        base_date=base_date,
        defaults={
            "threshold": PORTFOLIO_THRESHOLD,
            "rebalance_type": "daily",
            "portfolio_score": portfolio_score,
            "summary": build_portfolio_summary(scores),
            "sector_warning": sector_warning_for(scores),
        },
    )
    run.items.all().delete()

    for score in scores:
        if score_sum > 0:
            score_edge = max(score.total_score - PORTFOLIO_THRESHOLD, 0)
            weight = round((score_edge / score_sum) * 100, 2)
        else:
            weight = round(100.0 / len(scores), 2) if scores else 0
        PortfolioItem.objects.create(
            portfolio_run=run,
            stock=score.stock,
            score_snapshot=score,
            score=score.total_score,
            weight=weight,
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
    stock = Stock.objects.get(ticker=ticker)
    score = stock.scores.filter(base_date=score_date).first() or stock.scores.first()
    metric = stock.financial_metrics.order_by("-base_date").first()
    prices = list(stock.prices.order_by("-date")[:PRICE_HISTORY_DAYS])
    prices.reverse()
    return {
        "stock": stock,
        "score": score,
        "metric": metric,
        "prices": prices,
    }


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

    dates = sorted({row_date for stock in weighted_stocks for row_date in stock["prices"]})
    series = []
    for row_date in dates:
        portfolio_value = 0
        active_weight = 0
        for stock in weighted_stocks:
            if row_date in stock["prices"]:
                stock["last_price"] = stock["prices"][row_date]
            if stock["last_price"]:
                active_weight += stock["weight"]
                portfolio_value += stock["weight"] * (stock["last_price"] / stock["start_price"])
        if active_weight:
            series.append({"date": row_date, "value": round((portfolio_value / active_weight) * 100, 4)})
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

    price_dates = sorted(list(
        PriceDaily.objects.filter(date__gte=start_date, date__lte=end_date)
        .values_list("date", flat=True)
        .distinct()
    ))

    if len(price_dates) < 2:
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
            "summary": "백테스트를 위한 충분한 가격 데이터가 없습니다.",
        }

    snapshots = ScoreSnapshot.objects.filter(
        base_date__gte=start_date,
        base_date__lte=end_date,
        reliability_score__gte=MIN_RELIABILITY_SCORE,
        company_score__gte=MIN_COMPONENT_SCORE,
        timing_score__gte=MIN_COMPONENT_SCORE,
        stock__is_active=True,
        stock__is_tradable=True,
        stock__is_universe_included=True,
        stock__low_liquidity_flag=False,
        fail_safe_flag=False
    ).select_related("stock")

    portfolio_by_date = {}
    for snap in snapshots:
        portfolio_by_date.setdefault(snap.base_date, []).append(snap)

    benchmark_series_raw, benchmark_source = kospi_benchmark_series(start_date, end_date)
    if not benchmark_series_raw:
        benchmark_series_raw = market_proxy_benchmark_series(start_date, end_date)

    portfolio_value = 100.0
    portfolio_series = []

    prices_raw = PriceDaily.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).values("stock_id", "date", "close_price")

    price_map = {}
    for p in prices_raw:
        price_map.setdefault(p["stock_id"], {})[p["date"]] = float(p["close_price"])

    active_portfolio = []

    for i, current_date in enumerate(price_dates):
        if current_date in portfolio_by_date:
            day_scores = portfolio_by_date[current_date]
            valid_items = []
            for score in day_scores:
                adjusted_score = score_for_risk(score, risk_type)
                company_score = company_score_for_risk(score, risk_type)
                timing_score = timing_score_for_risk(score, risk_type)
                if company_score >= MIN_COMPONENT_SCORE and timing_score >= MIN_COMPONENT_SCORE:
                    valid_items.append({
                        "ticker": score.stock.ticker,
                        "total_score": adjusted_score,
                    })

            score_sum = sum(max(item["total_score"] - PORTFOLIO_THRESHOLD, 0) for item in valid_items)
            active_portfolio = []
            for item in valid_items:
                if score_sum > 0:
                    weight = max(item["total_score"] - PORTFOLIO_THRESHOLD, 0) / score_sum
                else:
                    weight = 1.0 / len(valid_items) if valid_items else 0
                active_portfolio.append((item["ticker"], weight))

        daily_return = 0.0
        if i < len(price_dates) - 1:
            next_date = price_dates[i + 1]
            total_weighted_return = 0.0
            total_active_weight = 0.0

            for ticker, weight in active_portfolio:
                stock_prices = price_map.get(ticker, {})
                p_curr = stock_prices.get(current_date)
                p_next = stock_prices.get(next_date)
                if p_curr and p_next and p_curr > 0:
                    ret = (p_next / p_curr) - 1.0
                    total_weighted_return += ret * weight
                    total_active_weight += weight

            if total_active_weight > 0:
                daily_return = (total_weighted_return / total_active_weight) * 100.0

        portfolio_series.append({
            "date": current_date,
            "value": round(portfolio_value, 4)
        })

        portfolio_value *= (1.0 + daily_return / 100.0)

    series, win_rate, max_drawdown = align_backtest_series(portfolio_series, benchmark_series_raw, len(active_portfolio))
    portfolio_return = series[-1]["portfolioReturn"] if series else 0
    benchmark_return = series[-1]["benchmarkReturn"] if series else 0
    alpha = round(portfolio_return - benchmark_return, 2)

    current_portfolio_payload = build_dynamic_portfolio_payload(risk_type=risk_type)
    current_item_count = len(current_portfolio_payload.get("items", []))

    return {
        "benchmark": benchmark.upper(),
        "benchmarkSource": benchmark_source,
        "period": period,
        "periodLabel": BACKTEST_PERIODS[period]["label"],
        "startDate": series[0]["date"] if series else start_date.isoformat(),
        "endDate": series[-1]["date"] if series else end_date.isoformat(),
        "rebalanceType": "daily",
        "portfolioReturn": round(portfolio_return, 2),
        "benchmarkReturn": round(benchmark_return, 2),
        "alpha": alpha,
        "winRate": win_rate,
        "maxDrawdown": max_drawdown,
        "itemCount": current_item_count,
        "series": series,
        "summary": f"현재 {RISK_LABELS[risk_type]} 추천 전략으로 과거 {BACKTEST_PERIODS[period]['label']} 동안 매일 리밸런싱하며 운영했다고 가정하고 시뮬레이션한 결과입니다.",
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
    if cached:
        return cached, True

    best_cards = sorted(score.score_cards or [], key=lambda card: card.get("score", 0), reverse=True)
    worst_cards = sorted(score.score_cards or [], key=lambda card: card.get("score", 100))
    positive_title = best_cards[0]["title"] if best_cards else "핵심 지표"
    negative_title = worst_cards[0]["title"] if worst_cards else "위험 지표"
    upside = 0
    if metric and metric.current_price and metric.target_price:
        upside = round((metric.target_price - metric.current_price) / metric.current_price * 100, 1)

    component_pass = score.company_score >= MIN_COMPONENT_SCORE and score.timing_score >= MIN_COMPONENT_SCORE
    pass_text = "포트폴리오 후보 조건을 통과합니다" if component_pass else "포트폴리오 후보 조건은 추가 확인이 필요합니다"
    positive = f"{stock.name}은 {positive_title} 점수가 강하고, 회사 {score.company_score:.1f}점·타이밍 {score.timing_score:.1f}점으로 {RISK_LABELS[risk_type]} 기준 {pass_text}."
    negative = f"다만 {negative_title} 항목과 '{score.warning or '단기 변동성'}' 이슈는 진입 전 확인이 필요합니다."
    conclusion = f"목표가 기준 상승 여력은 약 {upside}%이며, 현재 판단은 '{score.verdict}'입니다. 본 결과는 투자 참고용 분석입니다."

    comment = AICommentCache.objects.create(
        stock=stock,
        base_date=score.base_date,
        risk_type=risk_type,
        positive=positive,
        negative=negative,
        conclusion=conclusion,
        provider="local-mvp",
    )
    return comment, False
